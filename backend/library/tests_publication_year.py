"""Tests for library/utils/publication_year.py. No network: Open Library is faked."""
import datetime
import re
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from library.models import Book
from library.utils.publication_year import (
    FirstPublishedLookup, parse_edition_year, parse_year, pick_first_year,
)

THIS_YEAR = datetime.date.today().year


class ParseYearTests(SimpleTestCase):
    def test_reads_common_date_formats(self):
        self.assertEqual(parse_year("June 1920"), 1920)
        self.assertEqual(parse_year("1925-04-10"), 1925)
        self.assertEqual(parse_year("c1965"), 1965)
        self.assertEqual(parse_year("Dec 01, 1925"), 1925)
        self.assertEqual(parse_year(1813), 1813)

    def test_rejects_impossible_years(self):
        self.assertIsNone(parse_year(0))
        self.assertIsNone(parse_year("0"))
        self.assertIsNone(parse_year(THIS_YEAR + 5))
        self.assertIsNone(parse_year("12345"))
        self.assertIsNone(parse_year(None))
        self.assertIsNone(parse_year(""))
        self.assertIsNone(parse_year(True))

    def test_edition_years_use_edition_limits(self):
        self.assertIsNone(parse_edition_year("1200"))  # Edition model minimum is 1500
        self.assertIsNone(parse_edition_year(THIS_YEAR + 1))  # not printed yet
        self.assertEqual(parse_edition_year("1611"), 1611)


class PickFirstYearTests(SimpleTestCase):
    def test_ignores_a_single_misdated_edition(self):
        # The Great Gatsby: one edition says 1920, many say 1925.
        years = [1920] + [1925] * 23 + [1926] * 4 + [2004] * 10
        self.assertEqual(pick_first_year(years), 1925)

    def test_keeps_a_well_attested_first_year(self):
        self.assertEqual(pick_first_year([1965] * 12 + [1966] * 3 + [2005]), 1965)

    def test_uses_a_count_function_when_given(self):
        counts = {1777: 1, 1954: 1, 1955: 9, 1956: 4}
        self.assertEqual(pick_first_year(counts, counts.get), 1955)

    def test_skips_a_placeholder_year_shared_by_a_few_editions(self):
        # Middlemarch: three undated printings filed under "1800".
        counts = {1800: 3, 1871: 5, 1872: 2, 1873: 2}
        self.assertEqual(pick_first_year(counts, counts.get), 1871)

    def test_keeps_a_well_attested_first_year_before_sparse_reprints(self):
        # Moby Dick: 9 editions in 1851, then nothing recorded until 1892.
        counts = {1851: 9, 1892: 2, 1900: 2}
        self.assertEqual(pick_first_year(counts, counts.get), 1851)

    def test_unconfirmed_years_fall_back_to_the_first_close_pair(self):
        # A newer book with one edition a year: nothing is shared, take 2019.
        self.assertEqual(pick_first_year([1672, 2019, 2020, 2022]), 2019)

    def test_a_single_edition_book_keeps_its_year(self):
        self.assertEqual(pick_first_year(["March 2021"]), 2021)

    def test_no_usable_years_means_unknown(self):
        self.assertIsNone(pick_first_year([]))
        self.assertIsNone(pick_first_year([0, None, "n.d."]))


class FakeOpenLibrary:
    """Answers the two search queries FirstPublishedLookup makes."""

    def __init__(self, works):
        self.works = works  # work id -> {year: edition count}
        self.calls = 0

    def __call__(self, path, params=None):
        self.calls += 1
        q = params["q"]
        match = re.fullmatch(r"key:/works/(\w+) AND publish_year:(\d+)", q)
        if match:
            key, year = match.group(1), int(match.group(2))
            n = self.works.get(key, {}).get(year, 0)
            return {"docs": [{"key": f"/works/{key}", "editions": {"numFound": n}}] if n else []}
        keys = re.findall(r"/works/(\w+)", q)
        return {"docs": [
            {"key": f"/works/{k}", "publish_year": list(self.works[k]),
             "first_publish_year": min(self.works[k])}
            for k in keys if k in self.works
        ]}


class LookupTests(SimpleTestCase):
    def test_looks_up_many_works(self):
        ol = FakeOpenLibrary({
            "OL468431W": {1920: 1, 1925: 23, 1926: 4},  # The Great Gatsby
            "OL893414W": {1965: 12, 1966: 3},           # Dune
        })
        years = FirstPublishedLookup(fetch=ol).years(["OL468431W", "/works/OL893414W", "OL1W"])
        self.assertEqual(years, {"OL468431W": 1925, "OL893414W": 1965, "OL1W": None})

    def test_unreachable_open_library_means_unknown(self):
        lookup = FirstPublishedLookup(fetch=lambda path, params=None: None)
        self.assertEqual(lookup.years(["OL893414W"]), {"OL893414W": None})


class FixPublicationYearsCommandTests(TestCase):
    def setUp(self):
        self.ol = FakeOpenLibrary({"OL893414W": {1965: 12, 1966: 3}})
        self.dune = Book.objects.create(title="Dune", book_id="OL893414W", year_published=2003)
        self.mystery = Book.objects.create(title="Unknown", book_id="OL1W", year_published=1999)
        self.local = Book.objects.create(title="Local", book_id="not-an-ol-id", year_published=1990)

    def run_command(self, *args):
        from library.management.commands import fix_publication_years
        original = fix_publication_years.FirstPublishedLookup
        fix_publication_years.FirstPublishedLookup = lambda: original(fetch=self.ol)
        try:
            out = StringIO()
            call_command("fix_publication_years", *args, stdout=out)
            return out.getvalue()
        finally:
            fix_publication_years.FirstPublishedLookup = original

    def test_dry_run_changes_nothing(self):
        out = self.run_command("--dry-run")
        self.assertIn("Dune: 2003 -> 1965", out)
        self.dune.refresh_from_db()
        self.assertEqual(self.dune.year_published, 2003)

    def test_corrects_known_books_and_leaves_the_rest(self):
        self.run_command()
        for book in (self.dune, self.mystery, self.local):
            book.refresh_from_db()
        self.assertEqual(self.dune.year_published, 1965)
        self.assertEqual(self.mystery.year_published, 1999)  # Open Library had nothing
        self.assertEqual(self.local.year_published, 1990)    # not an Open Library work
