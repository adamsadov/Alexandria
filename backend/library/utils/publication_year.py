"""
When was a book first published? One answer for every importer.

Open Library has two kinds of records:

* an **edition** is one printing (an ISBN, a publisher, a year);
* a **work** is the book itself, grouping all of its editions.

Our ``Book.year_published`` is the work's original publication year and
``Edition.publication_year`` is each printing's own year.

The work record's own ``first_publish_date`` is rarely filled in and is often
wrong (Lord of the Rings: "2001"). Open Library's search index instead lists
every year any edition was published (``publish_year``) and reports the
earliest as ``first_publish_year``. That's usually right, but one mistyped
edition is enough to throw it off (Lolita: 1777, Interview with the Vampire:
1672, The Great Gatsby: 1920). Catalogers also file undated old printings
under placeholder years like "1800", sometimes several of them (Middlemarch,
The Scarlet Letter, David Copperfield all "first published" in 1800).

So we take the earliest year that at least two editions agree on. A year
that sits alone, with no edition in the decade after it, needs more: real
first editions are recorded many times over (Moby Dick: 9 in 1851, before a
sparse run of reprints), while placeholders and typos are a handful at most.
We only fall back to an unconfirmed year when nothing passes (a new book
with one edition, say).
"""
import datetime
import re
import time
from collections import Counter

import requests

OPEN_LIBRARY = "https://openlibrary.org"
USER_AGENT = "AlexandriaSeed/1.0 (student book-sharing project)"

EARLIEST_BOOK_YEAR = 1000  # Book.year_published validator
EARLIEST_EDITION_YEAR = 1500  # Edition.publication_year validator

# How many editions must share a year before we believe it.
MIN_EDITIONS = 2
# A year with no edition in the MAX_GAP years after it must be shared by
# at least MIN_EDITIONS_ALONE editions.
MAX_GAP = 10
MIN_EDITIONS_ALONE = 5
# How many of the earliest years to check before giving up on confirming one.
MAX_PROBES = 6
# Works per search request when looking up many at once.
BATCH_SIZE = 40

_YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def parse_year(value, earliest=EARLIEST_BOOK_YEAR, latest=None):
    """
    A plausible year from an int or a date string ("June 1920",
    "1925-04-10", "c1965"), or None. Years outside earliest..latest
    (default: next year) are treated as junk.
    """
    if latest is None:
        latest = datetime.date.today().year + 1
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        candidates = [value]
    else:
        candidates = [int(y) for y in _YEAR.findall(str(value))]
    for year in candidates:
        if earliest <= year <= latest:
            return year
    return None


def parse_edition_year(value):
    """parse_year with the limits Edition.publication_year accepts."""
    return parse_year(value, EARLIEST_EDITION_YEAR, datetime.date.today().year)


def pick_first_year(years, count_editions=None):
    """
    The original publication year from the years a work's editions were
    published in.

    years: edition years or dates, in any order; junk is ignored.
    count_editions(year) -> how many editions came out that year. Without it,
        repeats in ``years`` are counted (pass one entry per edition).

    Returns the earliest year that at least MIN_EDITIONS editions share, or
    MIN_EDITIONS_ALONE if no edition follows within MAX_GAP years. If none of
    the earliest MAX_PROBES years qualifies, returns the earliest year with
    another edition close behind it (within 2 years), else the earliest year.
    None when there are no usable years.
    """
    parsed = [y for y in (parse_year(v) for v in years) if y]
    if not parsed:
        return None
    if count_editions is None:
        counts = Counter(parsed)
        count_editions = counts.__getitem__

    distinct = sorted(set(parsed))
    following = dict(zip(distinct, distinct[1:]))  # year -> next year with an edition

    for year in distinct[:MAX_PROBES]:
        alone = year in following and following[year] - year > MAX_GAP
        if count_editions(year) >= (MIN_EDITIONS_ALONE if alone else MIN_EDITIONS):
            return year
    for year in distinct:
        if year in following and following[year] - year <= 2:
            return year
    return distinct[0]


def get_json(path, params=None, tries=5, session=None):
    """GET an Open Library JSON endpoint, retrying politely. None on failure or 404."""
    url = path if path.startswith("http") else OPEN_LIBRARY + path
    http = session or requests
    for attempt in range(tries):
        try:
            r = http.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt + 1)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            time.sleep(2 ** attempt + 1)
    return None


def _work_key(key):
    """'/works/OL893414W' or 'OL893414W' -> 'OL893414W'."""
    return key.rsplit("/", 1)[-1]


class FirstPublishedLookup:
    """
    Looks up original publication years on Open Library.

        years = FirstPublishedLookup().years(["OL893414W", "OL468431W"])
        # {"OL893414W": 1965, "OL468431W": 1925}

    Works Open Library doesn't know, or that have no usable years, map to
    None; so does everything if Open Library can't be reached. Callers keep
    whatever they had in that case rather than guessing.
    """

    def __init__(self, fetch=get_json):
        self.fetch = fetch

    def year(self, work_key):
        return self.years([work_key]).get(_work_key(work_key))

    def years(self, work_keys):
        keys = list(dict.fromkeys(_work_key(k) for k in work_keys))
        result = {k: None for k in keys}
        for start in range(0, len(keys), BATCH_SIZE):
            chunk = keys[start:start + BATCH_SIZE]
            query = "key:(" + " OR ".join(f"/works/{k}" for k in chunk) + ")"
            data = self.fetch("/search.json", {
                "q": query,
                "fields": "key,first_publish_year,publish_year",
                "limit": len(chunk),
            }) or {}
            for doc in data.get("docs", []):
                key = _work_key(doc.get("key", ""))
                if key not in result:
                    continue
                years = doc.get("publish_year") or [doc.get("first_publish_year")]
                result[key] = pick_first_year(years, lambda y, k=key: self.editions_in(k, y))
        return result

    def editions_in(self, work_key, year):
        """How many of the work's editions Open Library dates to ``year``."""
        data = self.fetch("/search.json", {
            "q": f"key:/works/{_work_key(work_key)} AND publish_year:{year}",
            "fields": "key,editions",
            "limit": 1,
        }) or {}
        docs = data.get("docs") or []
        if not docs:
            return 0
        return (docs[0].get("editions") or {}).get("numFound", 0)
