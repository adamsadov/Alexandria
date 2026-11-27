"""`manage.py import_book` and the uploader, with Open Library stubbed out."""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from library.book_upload.openlibrary_uploader import import_work
from library.models import Author, Book, Edition

WORK = {
    "key": "/works/OL1W",
    "title": "Test Book",
    "description": {"value": "A summary."},
    "first_publish_year": 1990,
    "subjects": ["Fantasy fiction"],
    "authors": [{"author": {"key": "/authors/OL1A"}}],
}
AUTHORS = [{"key": "/authors/OL1A", "name": "Ann Author", "bio": {"value": "Wrote things."}}]
EDITIONS = [
    {"key": "/books/OL1M", "isbn_13": ["9780000000001"], "publish_date": "May 1990",
     "physical_format": "hardcover", "publishers": ["Pub"], "covers": [11]},
    {"key": "/books/OL2M", "isbn_10": ["0000000002"], "publish_date": "2005"},
    {"key": "/books/OL3M", "publish_date": "2010"},  # no ISBN: skipped
]


def data(**overrides):
    return {"work": dict(WORK, **overrides), "authors": AUTHORS, "editions": EDITIONS}


@mock.patch("library.book_upload.openlibrary_uploader.get_wikipedia_image_for_author", return_value=None)
class ImportWorkTests(TestCase):
    def test_imports_book_author_and_editions(self, _wiki):
        book = import_work(data())
        self.assertEqual((book.book_id, book.title, book.year_published), ("OL1W", "Test Book", 1990))
        self.assertEqual(book.summary, "A summary.")
        self.assertEqual(list(book.authors.values_list("name", flat=True)), ["Ann Author"])
        self.assertEqual(Author.objects.get().biography, "Wrote things.")
        self.assertEqual(sorted(Edition.objects.values_list("isbn", "publication_year")),
                         [("0000000002", 2005), ("9780000000001", 1990)])
        self.assertTrue(book.editions.get(isbn="9780000000001").related_edition_image.get().is_primary)

    def test_reimport_adds_nothing_twice(self, _wiki):
        import_work(data())
        import_work(data())
        self.assertEqual((Book.objects.count(), Author.objects.count(), Edition.objects.count()), (1, 1, 2))

    def test_failure_leaves_nothing_behind(self, _wiki):
        with mock.patch("library.book_upload.openlibrary_uploader.LibraryUpload.upload_editions",
                        side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                import_work(data())
        self.assertFalse(Book.objects.exists())
        self.assertFalse(Author.objects.exists())


@mock.patch("library.management.commands.import_book.time.sleep")
@mock.patch("library.book_upload.openlibrary_uploader.get_wikipedia_image_for_author", return_value=None)
class ImportBookCommandTests(TestCase):
    def run_command(self, *args, fetched=None):
        def fake_fetch(title=None, work_id=None):
            if (title or work_id) == "missing":
                raise ValueError("No results found for 'missing'")
            return fetched or data()
        out, err = StringIO(), StringIO()
        with mock.patch("library.management.commands.import_book.fetch_work", side_effect=fake_fetch) as f:
            call_command("import_book", *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue(), f

    def test_by_work_id(self, _wiki, _sleep):
        out, _err, fetch = self.run_command("--work-id", "OL1W")
        fetch.assert_called_once_with(work_id="OL1W")
        self.assertIn("Imported Test Book (OL1W): 2 editions", out)

    def test_batch_survives_a_failed_book(self, _wiki, _sleep):
        out, err, _f = self.run_command("missing", "Test Book")
        self.assertIn("Failed: missing", err)
        self.assertIn("1 imported, 1 failed", out)
        self.assertTrue(Book.objects.filter(book_id="OL1W").exists())

    def test_all_failed_is_an_error(self, _wiki, _sleep):
        with self.assertRaises(CommandError):
            self.run_command("missing")

    def test_needs_something_to_import(self, _wiki, _sleep):
        with self.assertRaises(CommandError):
            call_command("import_book", stdout=StringIO())
