"""Search: matching, ranking and query count for /api/search-bar/ (search/catalog.py)."""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from library.models import Author, Book, BookAuthor, CoverImage, Edition
from search.catalog import clean_isbn, isbn_variants


class IsbnHelperTests(TestCase):
    def test_cleans_dashes_and_spaces(self):
        self.assertEqual(clean_isbn("978-0-441-01359-3"), "9780441013593")
        self.assertEqual(clean_isbn("0 441 01359 7"), "0441013597")
        self.assertEqual(clean_isbn("044101359x"), "044101359X")

    def test_rejects_non_isbns(self):
        self.assertIsNone(clean_isbn("dune"))
        self.assertIsNone(clean_isbn("12345"))

    def test_converts_between_10_and_13_digits(self):
        self.assertEqual(isbn_variants("0441013597"), {"0441013597", "9780441013593"})
        self.assertEqual(isbn_variants("9780441013593"), {"9780441013593", "0441013597"})


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def book(title, author, isbn=None, rating=0, cover=None):
            b = Book.objects.create(title=title, book_id=f"OL{Book.objects.count() + 1}W",
                                    average_rating=rating)
            a, _ = Author.objects.get_or_create(name=author, defaults={"author_id": f"a-{author}"})
            BookAuthor.objects.create(book=b, author=a)
            if isbn:
                e = Edition.objects.create(book=b, isbn=isbn, kind="Paperback", language="eng",
                                           publication_year=2005, is_primary=True)
                if cover:
                    CoverImage.objects.create(edition=e, image_url=cover, is_primary=True)
            return b

        cls.stone = book("Harry Potter and the Philosopher's Stone", "J.K. Rowling", rating=4.5)
        cls.chamber = book("Harry Potter and the Chamber of Secrets", "J.K. Rowling", rating=4.4)
        cls.hobbit = book("The Hobbit", "J.R.R. Tolkien", rating=4.3)
        cls.lotr = book("The Lord of the Rings", "J.R.R. Tolkien", rating=4.5)
        cls.flies = book("Lord of the Flies", "William Golding", rating=3.7)
        cls.dune = book("Dune", "Frank Herbert", isbn="9780441013593", rating=4.3,
                        cover="https://covers.example/dune.jpg")
        cls.messiah = book("Dune Messiah", "Frank Herbert", rating=3.9)
        cls.shining = book("The Shining", "Stephen King", rating=4.2)
        cls.levitt = book("Freakonomics", "Steven D. Levitt", rating=4.0)

    def setUp(self):
        self.client = APIClient()

    def search(self, q, **params):
        response = self.client.get("/api/search-bar/", {"q": q, **params})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def titles(self, q, **params):
        return [b["title"] for b in self.search(q, **params)["books"]]

    def test_typos_still_find_the_book(self):
        self.assertTrue(self.titles("hary poter")[0].startswith("Harry Potter"))
        self.assertEqual(self.titles("lord of the rngs")[0], "The Lord of the Rings")

    def test_author_typo_finds_the_author_and_their_books(self):
        result = self.search("tolkein")
        self.assertEqual(result["authors"][0]["name"], "J.R.R. Tolkien")
        self.assertEqual({b["title"] for b in result["books"]}, {"The Hobbit", "The Lord of the Rings"})

    def test_closest_author_wins(self):
        result = self.search("steven king")
        self.assertEqual(result["authors"][0]["name"], "Stephen King")
        self.assertEqual(result["books"][0]["title"], "The Shining")

    def test_exact_title_beats_longer_titles(self):
        self.assertEqual(self.titles("dune")[:2], ["Dune", "Dune Messiah"])
        self.assertEqual(self.titles("lord of the rings")[0], "The Lord of the Rings")

    def test_isbn_with_dashes_or_the_other_length(self):
        self.assertEqual(self.titles("978-0-441-01359-3")[0], "Dune")
        self.assertEqual(self.titles("0441013597")[0], "Dune")  # stored as ISBN-13

    def test_short_queries_match_by_prefix(self):
        self.assertEqual(self.titles("du"), ["Dune", "Dune Messiah"])

    def test_no_match_and_empty_query(self):
        self.assertEqual(self.search("zzzzqqqq"), {"books": [], "authors": []})
        self.assertEqual(self.search("   "), {"books": [], "authors": []})

    def test_limit_and_offset(self):
        everything = self.titles("harry potter")
        self.assertEqual(len(everything), 2)
        self.assertEqual(self.titles("harry potter", limit=1), everything[:1])
        self.assertEqual(self.titles("harry potter", limit=1, offset=1), everything[1:2])
        self.assertEqual(len(self.titles("harry potter", limit="junk")), 2)  # falls back to default

    def test_result_shape_and_cover(self):
        dune = self.search("dune")["books"][0]
        self.assertEqual(dune["id"], self.dune.id)
        self.assertEqual(dune["book_id"], self.dune.book_id)
        self.assertEqual(dune["authors"], ["Frank Herbert"])
        self.assertEqual(dune["cover_image"], "https://covers.example/dune.jpg")
        self.assertEqual(dune["type"], "book")

    def test_query_count_does_not_grow_with_results(self):
        with CaptureQueriesContext(connection) as one:
            self.search("dune", limit=1)
        with CaptureQueriesContext(connection) as many:
            self.search("the", limit=50)
        self.assertEqual(len(one.captured_queries), len(many.captured_queries))
