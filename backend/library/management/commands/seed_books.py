"""
Load the shared book catalog into the local database.

    python manage.py seed_books           # add/update the catalog (safe to re-run)
    python manage.py seed_books --clear   # delete ALL books first, then load

Reads library/fixtures/seed_books.json (built by `build_seed_data`), so every
developer gets the same books, editions, authors and Discover shelves. No
network needed.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from discovery.models import FeaturedShelf
from library.models import (
    Author, Book, BookAuthor, BookGenre, CoverImage, Edition, Genre,
    Publisher, Shelf, ShelfEdition, User,
)
from library.utils.authors import author_hash, find_author, remember_key
from library.utils.publication_year import parse_edition_year

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "seed_books.json"
CURATOR_USERNAME = "alexandria"
CURATOR_EMAIL = "curator@alexandria.local"


def cover_url(cover_id):
    return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


class Command(BaseCommand):
    help = "Load the shared seed catalog (books, editions, authors, Discover shelves)"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(FIXTURE))
        parser.add_argument("--clear", action="store_true",
                            help="Delete every book, author, edition and featured shelf first")

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"{path} not found. Run `python manage.py build_seed_data` first.")
        data = json.loads(path.read_text(encoding="utf-8"))

        with transaction.atomic():
            if opts["clear"]:
                FeaturedShelf.objects.all().delete()
                Book.objects.all().delete()  # cascades to editions, covers, links
                Author.objects.all().delete()
                Publisher.objects.all().delete()
                Genre.objects.all().delete()
                self.stdout.write("Cleared existing catalog.")

            authors = self._authors(data["authors"])
            books = self._books(data["books"], authors)
            self._featured(data.get("featured", []), books)

        self.stdout.write(self.style.SUCCESS(
            f"Catalog loaded: {Book.objects.count()} books, {Edition.objects.count()} editions, "
            f"{Author.objects.count()} authors, {Genre.objects.count()} genres, "
            f"{FeaturedShelf.objects.filter(is_active=True).count()} Discover shelves."))

    # ---------------------------------------------------------------- authors
    def _authors(self, authors):
        out = {}
        for key, a in authors.items():
            fields = {"name": a["name"], "biography": a.get("bio"), "author_image": a.get("image")}
            # A key merged into another author (merge_authors) keeps pointing there.
            author = find_author(key)
            if author is None:
                author = Author.objects.create(author_id=author_hash(key), **fields)
            elif author.author_id == author_hash(key):
                Author.objects.filter(pk=author.pk).update(**fields)
            remember_key(author, key)
            # Other Open Library records for the same person (see build_seed_data),
            # so a later import_book that meets one of them links to this author.
            for alias in a.get("aliases", []):
                remember_key(author, alias)
            out[key] = author
        return out

    # ------------------------------------------------------------------ books
    def _books(self, books, authors):
        genres, publishers, out = {}, {}, {}

        for b in books:
            book, _ = Book.objects.update_or_create(
                book_id=b["work"],  # Open Library work id, as in the uploader
                defaults={
                    "title": b["title"],
                    "summary": b.get("summary"),
                    "year_published": b.get("year"),
                    "original_language": "eng",
                    "average_rating": b.get("rating") or 0,
                },
            )
            out[b["work"]] = book

            for key in b["authors"]:
                if key in authors:
                    BookAuthor.objects.get_or_create(book=book, author=authors[key])

            for name in b.get("genres") or ["fiction"]:
                if name not in genres:
                    genres[name], _ = Genre.objects.get_or_create(name=name[:100])
                BookGenre.objects.get_or_create(book=book, genre=genres[name])

            for i, e in enumerate(b["editions"]):
                pub = None
                if e.get("publisher"):
                    name = e["publisher"][:100]
                    if name not in publishers:
                        publishers[name], _ = Publisher.objects.get_or_create(name=name)
                    pub = publishers[name]
                # The printing's own year; blank if unknown, never the book's year.
                year = parse_edition_year(e.get("year"))
                edition, _ = Edition.objects.update_or_create(
                    isbn=e["isbn"],
                    defaults={
                        "book": book,
                        "publisher": pub,
                        "kind": e["kind"],
                        "is_primary": i == 0,
                        "publication_year": year,
                        "language": e.get("language") or "eng",
                        "page_count": e.get("pages"),
                    },
                )
                for j, cid in enumerate(e.get("covers", [])):
                    CoverImage.objects.update_or_create(
                        edition=edition, image_url=cover_url(cid),
                        defaults={"is_primary": i == 0 and j == 0},
                    )
        return out

    # ------------------------------------------------------- Discover shelves
    def _featured(self, featured, books):
        if not featured:
            return
        curator, created = User.objects.get_or_create(
            username=CURATOR_USERNAME,
            defaults={"email": CURATOR_EMAIL, "first_name": "Alexandria"},
        )
        if created:
            curator.set_unusable_password()  # nobody can log in as the curator
            curator.save()

        for order, f in enumerate(featured):
            shelf, _ = Shelf.objects.update_or_create(
                user=curator, name=f["title"],
                defaults={"shelf_desc": f["description"], "shelf_type": "Custom", "is_private": False},
            )
            ShelfEdition.objects.filter(shelf=shelf).delete()
            for work in f["works"]:
                book = books.get(work)
                edition = book and (book.editions.filter(is_primary=True).first() or book.editions.first())
                if edition:
                    ShelfEdition.objects.create(shelf=shelf, edition=edition)
            FeaturedShelf.objects.update_or_create(
                display_title=f["title"],
                defaults={"shelf": shelf, "description": f["description"],
                          "display_type": f["display_type"], "display_order": order, "is_active": True},
            )
