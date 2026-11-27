"""The seed catalog gives one author per person, even when Open Library has several records (#24)."""
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from library.management.commands.build_seed_data import collapse_duplicate_authors
from library.models import Author
from library.utils.authors import find_author


def book(work, title, *authors):
    return {"work": work, "title": title, "summary": "", "year": 1949, "rating": 4.0,
            "authors": list(authors), "genres": [], "editions": []}


class SeedBooksAliasTests(TestCase):
    def seed(self, catalog):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "seed.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            call_command("seed_books", "--file", str(path), stdout=StringIO())

    def test_one_author_per_person_with_all_books(self):
        catalog = {
            "authors": {"OL118077A": {"name": "George Orwell", "bio": "Bio", "image": None,
                                      "aliases": ["OL15318546A"]}},
            "books": [book("OLW1", "Animal Farm", "OL118077A"),
                      book("OLW2", "Nineteen Eighty-Four", "OL118077A")],
            "featured": [],
        }
        self.seed(catalog)
        self.seed(catalog)  # re-running stays at one author
        orwell = Author.objects.get(name="George Orwell")
        self.assertEqual(sorted(orwell.related_author_books.values_list("book__title", flat=True)),
                         ["Animal Farm", "Nineteen Eighty-Four"])
        # A later import that meets the other Open Library record links to the same author.
        self.assertEqual(find_author("OL15318546A"), orwell)

    def test_shipped_catalog_has_no_duplicate_people(self):
        call_command("seed_books", stdout=StringIO())
        orwell = Author.objects.get(name="George Orwell")
        self.assertEqual(sorted(orwell.related_author_books.values_list("book__title", flat=True)),
                         ["Animal Farm", "Nineteen Eighty-Four"])
        for name in ["Stephen King", "Jay Asher", "Angie Thomas", "Elizabeth Kendall"]:
            self.assertEqual(Author.objects.filter(name__iexact=name).count(), 1, name)


class CollapseDuplicateAuthorsTests(SimpleTestCase):
    def test_merges_confirmed_and_keeps_namesake(self):
        authors = {
            "OL1A": {"name": "Ann Author", "bio": "Bio", "image": None},
            "OL9A": {"name": "Ann  Author ", "bio": None, "image": "img"},  # stub of OL1A
            "OL5A": {"name": "Ann Author", "bio": None, "image": None},     # a different person
        }
        books = [book("W1", "First", "OL1A"), book("W2", "Second", "OL9A"),
                 book("W3", "Both", "OL1A", "OL9A"), book("W4", "Gardening", "OL5A")]
        pages = {
            "/authors/OL1A.json": {"key": "/authors/OL1A", "name": "Ann Author"},
            "/authors/OL5A.json": {"key": "/authors/OL5A", "name": "Ann Author"},
            "/authors/OL1A/works.json?limit=1000": {"entries": [{"title": "First"}]},
            "/authors/OL5A/works.json?limit=1000": {"entries": [{"title": "Gardening"}]},
        }
        merged = collapse_duplicate_authors(authors, books, fetch=lambda path, *a, **k: pages.get(path))
        self.assertEqual(merged, [("OL1A", ["OL9A"])])
        self.assertEqual(set(authors), {"OL1A", "OL5A"})
        self.assertEqual(authors["OL1A"], {"name": "Ann Author", "bio": "Bio", "image": "img", "aliases": ["OL9A"]})
        self.assertEqual([b["authors"] for b in books], [["OL1A"], ["OL1A"], ["OL1A"], ["OL5A"]])
