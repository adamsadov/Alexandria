"""Duplicate authors (#24): resolving OL author records and merging duplicates."""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from library.models import Author, AuthorKey, Book, BookAuthor
from library.utils.authors import (
    author_hash, follow_redirects, merge_into, normalize_name, resolve_author, same_person,
)


def fake_open_library(pages):
    """A get_json stand-in: path -> dict, None for anything unknown."""
    def fetch(path, *args, **kwargs):
        return pages.get(path)
    return fetch


def author_record(key, name, **extra):
    return {"key": f"/authors/{key}", "name": name, "type": {"key": "/type/author"}, **extra}


def works(*titles):
    return {"entries": [{"title": t} for t in titles]}


def works_path(key):
    return f"/authors/{key}/works.json?limit=1000"


# Two Open Library records for one Orwell, and an unrelated namesake.
ORWELL = {
    "/authors/OL118077A.json": author_record("OL118077A", "George Orwell",
                                             birth_date="25 June 1903", remote_ids={"wikidata": "Q3335"}),
    works_path("OL118077A"): works("Animal Farm", "Nineteen Eighty-Four", "Homage to Catalonia"),
    "/authors/OL15318546A.json": author_record("OL15318546A", "George Orwell"),
    works_path("OL15318546A"): works("Nineteen Eighty-Four", "1984"),
    "/authors/OL999A.json": author_record("OL999A", "George Orwell", birth_date="1971"),
    works_path("OL999A"): works("Gardening for Beginners"),
    "/works/OLW1.json": {"authors": [{"author": {"key": "/authors/OL118077A"}}]},
    "/works/OLW2.json": {"authors": [{"author": {"key": "/authors/OL15318546A"}}]},
    "/works/OLW3.json": {"authors": [{"author": {"key": "/authors/OL999A"}}]},
}


class NormalizeNameTests(SimpleTestCase):
    def test_initials_punctuation_case_and_spacing(self):
        expected = "jrr tolkien"
        for name in ["J.R.R. Tolkien", "J. R. R. Tolkien", "JRR Tolkien", "j r r tolkien ", "J.R.R.  TOLKIEN"]:
            self.assertEqual(normalize_name(name), expected, name)

    def test_accents(self):
        self.assertEqual(normalize_name("Gabriel García Márquez"), "gabriel garcia marquez")

    def test_different_names_differ(self):
        self.assertNotEqual(normalize_name("Stephen King"), normalize_name("Stephen Kings"))


class RedirectTests(SimpleTestCase):
    def test_follows_redirect_chain(self):
        fetch = fake_open_library({
            "/authors/OL2A.json": {"type": {"key": "/type/redirect"}, "location": "/authors/OL3A"},
            "/authors/OL3A.json": author_record("OL3A", "Jane Doe"),
        })
        start = {"key": "/authors/OL1A", "type": {"key": "/type/redirect"}, "location": "/authors/OL2A"}
        self.assertEqual(follow_redirects(start, fetch)["key"], "/authors/OL3A")

    def test_redirect_loop_gives_none(self):
        fetch = fake_open_library({
            "/authors/OL2A.json": {"type": {"key": "/type/redirect"}, "location": "/authors/OL1A"},
            "/authors/OL1A.json": {"type": {"key": "/type/redirect"}, "location": "/authors/OL2A"},
        })
        self.assertIsNone(follow_redirects(fetch("/authors/OL1A.json"), fetch))


class SamePersonTests(SimpleTestCase):
    fetch = staticmethod(fake_open_library(ORWELL))

    def test_shared_work_titles_confirm(self):
        self.assertTrue(same_person("OL118077A", "OL15318546A", self.fetch)[0])

    def test_name_alone_is_not_enough(self):
        match, reason = same_person("OL15318546A", "OL999A", self.fetch)
        self.assertFalse(match, reason)

    def test_conflicting_dates_win_over_shared_titles(self):
        pages = dict(ORWELL, **{works_path("OL999A"): works("Animal Farm")})
        match, reason = same_person("OL118077A", "OL999A", fake_open_library(pages))
        self.assertFalse(match)
        self.assertIn("birth date", reason)


def make_book(book_id, title, *authors):
    book = Book.objects.create(book_id=book_id, title=title)
    for author in authors:
        BookAuthor.objects.create(book=book, author=author)
    return book


def make_author(key, name="George Orwell", **fields):
    return Author.objects.create(author_id=author_hash(key), name=name, **fields)


class ResolveAuthorTests(TestCase):
    def setUp(self):
        self.orwell = make_author("OL118077A")
        make_book("OLW1", "Animal Farm", self.orwell)

    def test_redirected_key_resolves_to_existing_author(self):
        pages = dict(ORWELL, **{"/authors/OL118077A.json": ORWELL["/authors/OL118077A.json"]})
        old = {"key": "/authors/OL5A", "type": {"key": "/type/redirect"}, "location": "/authors/OL118077A"}
        author, created = resolve_author(old, fetch=fake_open_library(pages))
        self.assertFalse(created)
        self.assertEqual(author, self.orwell)
        self.assertEqual(AuthorKey.objects.get(key="OL5A").author, self.orwell)

    def test_known_duplicate_key_links_to_merged_author(self):
        AuthorKey.objects.create(author=self.orwell, key="OL15318546A")
        author, created = resolve_author(ORWELL["/authors/OL15318546A.json"], fetch=fake_open_library({}))
        self.assertEqual((author, created), (self.orwell, False))

    def test_new_duplicate_record_is_confirmed_and_linked(self):
        author, created = resolve_author(ORWELL["/authors/OL15318546A.json"], fetch=fake_open_library(ORWELL))
        self.assertEqual((author, created), (self.orwell, False))
        self.assertEqual(Author.objects.filter(name="George Orwell").count(), 1)
        self.assertEqual(set(self.orwell.ol_keys.values_list("key", flat=True)), {"OL118077A", "OL15318546A"})

    def test_namesake_without_evidence_gets_own_author(self):
        author, created = resolve_author(ORWELL["/authors/OL999A.json"], fetch=fake_open_library(ORWELL))
        self.assertTrue(created)
        self.assertNotEqual(author, self.orwell)
        self.assertEqual(author.author_id, author_hash("OL999A"))


class MergeTests(TestCase):
    def setUp(self):
        self.keeper = make_author("OL118077A", biography=None, author_image="https://via.placeholder.com/150")
        self.dupe = make_author("OL15318546A", biography="Eric Blair.", author_image="https://img/orwell.jpg")
        self.namesake = make_author("OL999A")
        self.animal_farm = make_book("OLW1", "Animal Farm", self.keeper)
        self.nineteen84 = make_book("OLW2", "Nineteen Eighty-Four", self.dupe)
        self.both = make_book("OLW9", "Essays", self.keeper, self.dupe)
        make_book("OLW3", "Gardening for Beginners", self.namesake)
        make_book("OLW4", "Gardening Again", self.namesake)

    def books_of(self, author):
        return set(author.related_author_books.values_list("book__title", flat=True))

    def test_merge_moves_links_and_skips_repeats(self):
        AuthorKey.objects.create(author=self.dupe, key="OL15318546A")
        moved = merge_into(self.keeper, [self.dupe])
        self.assertEqual(moved, 1)
        self.assertFalse(Author.objects.filter(pk=self.dupe.pk).exists())
        self.assertEqual(self.books_of(self.keeper), {"Animal Farm", "Nineteen Eighty-Four", "Essays"})
        self.assertEqual(BookAuthor.objects.filter(book=self.both).count(), 1)
        self.assertEqual(AuthorKey.objects.get(key="OL15318546A").author, self.keeper)
        self.keeper.refresh_from_db()
        self.assertEqual(self.keeper.biography, "Eric Blair.")
        self.assertEqual(self.keeper.author_image, "https://img/orwell.jpg")

    def run_command(self, *args):
        out = StringIO()
        with mock.patch("library.management.commands.merge_authors.get_json", fake_open_library(ORWELL)):
            call_command("merge_authors", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        before = (list(Author.objects.values_list("pk", flat=True).order_by("pk")),
                  list(BookAuthor.objects.values_list("pk", "author_id").order_by("pk")))
        out = self.run_command("--dry-run")
        self.assertIn("Would merge 1 duplicate", out)
        after = (list(Author.objects.values_list("pk", flat=True).order_by("pk")),
                 list(BookAuthor.objects.values_list("pk", "author_id").order_by("pk")))
        self.assertEqual(before, after)
        self.assertFalse(AuthorKey.objects.exists())

    def test_command_merges_confirmed_and_keeps_namesake(self):
        out = self.run_command()
        self.assertIn("not merged", out)
        self.assertEqual(Author.objects.filter(name="George Orwell").count(), 2)
        # The namesake has more books, so it must not have absorbed Orwell.
        self.assertEqual(self.books_of(self.namesake), {"Gardening for Beginners", "Gardening Again"})
        orwell = Author.objects.get(author_id=author_hash("OL118077A"))
        self.assertEqual(self.books_of(orwell), {"Animal Farm", "Nineteen Eighty-Four", "Essays"})
        self.assertEqual(set(orwell.ol_keys.values_list("key", flat=True)), {"OL118077A", "OL15318546A"})
