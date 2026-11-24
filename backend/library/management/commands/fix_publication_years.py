"""
Correct Book.year_published (the original publication year) from Open Library.

    python manage.py fix_publication_years --dry-run     # show what would change
    python manage.py fix_publication_years               # apply
    python manage.py fix_publication_years --book-id OL893414W

Works for every book whose book_id is an Open Library work id (OL...W), seeded
or imported. Uses the same rule as the importers (library/utils/publication_year.py).
Books Open Library can't date are left as they are. Edition years are never
touched: each edition keeps its own printing's year.
"""
import re

from django.core.management.base import BaseCommand

from library.models import Book
from library.utils.publication_year import FirstPublishedLookup

WORK_ID = re.compile(r"^OL\d+W$")


class Command(BaseCommand):
    help = "Correct books' original publication years using Open Library"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would change without saving")
        parser.add_argument("--book-id", help="Only this book (its Open Library work id)")
        parser.add_argument("--limit", type=int, default=0,
                            help="Only the first N books (0 for all)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        books = Book.objects.order_by("title")
        if options["book_id"]:
            books = books.filter(book_id=options["book_id"])
        books = [b for b in books if WORK_ID.match(b.book_id or "")]
        if options["limit"]:
            books = books[:options["limit"]]
        if not books:
            self.stdout.write(self.style.WARNING("No books with an Open Library work id to check."))
            return

        self.stdout.write(f"Looking up {len(books)} books on Open Library...")
        found = FirstPublishedLookup().years([b.book_id for b in books])

        changed = unknown = 0
        for book in books:
            year = found.get(book.book_id)
            if not year:
                unknown += 1
                continue
            if year == book.year_published:
                continue
            changed += 1
            self.stdout.write(f"  {book.title}: {book.year_published or 'none'} -> {year}")
            if not dry_run:
                book.year_published = year
                book.save(update_fields=["year_published"])

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {changed} of {len(books)} books; "
            f"{unknown} left unchanged because Open Library had no usable year."))
