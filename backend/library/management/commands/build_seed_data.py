"""
Build the shared seed catalog from Open Library.

    python manage.py build_seed_data            # writes library/fixtures/seed_books.json

This hits the network (~1,000 requests, a few minutes) and only needs to be run
when we want a new catalog. The output file is committed, so everyone else
just runs `python manage.py seed_books`, which loads it with no network.

What it collects:
  * the most-read works (Open Library "reading log" count) across a spread of
    subjects, plus every book the Discover page shows;
  * for each work: summary, first-publish year, rating, genres, authors;
  * up to MAX_EDITIONS English editions with an ISBN, preferring different
    formats (hardcover / paperback / ebook / audiobook) and editions with covers.
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

from library.utils.genre_utils import extract_genres_from_subjects

OL = "https://openlibrary.org"
HEADERS = {"User-Agent": "AlexandriaSeed/1.0 (student book-sharing project)"}
FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "seed_books.json"

MAX_EDITIONS = 4
MAX_AUTHORS_PER_BOOK = 3

# (Open Library subject query, how many of its most-read works to take)
SUBJECTS = [
    ("subject:fantasy", 60),
    ("subject:science_fiction", 50),
    ("subject:romance", 60),
    ("subject:mystery", 40),
    ("subject:thrillers", 40),
    ("subject:crime", 25),
    ("subject:horror", 30),
    ("subject:historical_fiction", 35),
    ("subject:young_adult_fiction", 40),
    ("subject:dystopias", 15),
    ("subject:adventure", 20),
    ("subject:humor", 15),
    ("subject:classic_literature", 50),
    ("subject:fiction", 60),
    ("subject:short_stories", 15),
    ("subject:plays", 10),
    ("subject:poetry", 15),
    ("subject:biography", 25),
    ("subject:autobiography", 15),
    ("subject:history", 25),
    ("subject:self-help", 25),
    ("subject:psychology", 15),
    ("subject:science", 15),
    ("subject:philosophy", 15),
    ("subject:business", 15),
    ("subject:true_crime", 10),
]

# Featured shelves on the Discover page. The first three are the books the
# page's built-in fallback shows (identified from its cover images), in order.
FEATURED = [
    {
        "title": "Top Rated this Week",
        "description": "Highly rated books that readers are loving right now",
        "display_type": "CAROUSEL",
        "works": ["OL893414W", "OL66554W", "OL3335245W", "OL318900W",
                  "OL267171W", "OL27448W", "OL1812933W", "OL1230613W"],
        "covers": [14637497, 8095021, 14813225, 489946, 107499, 8314545, 8401686, 14831243],
    },
    {
        "title": "Popular in Fiction",
        "description": "Trending fiction titles across all genres",
        "display_type": "CAROUSEL",
        "works": ["OL41943074W", "OL34028551W", "OL82563W", "OL8193465W",
                  "OL17076473W", "OL2827199W"],
        "covers": [14839882, 14576376, 14348601, 13499486, 8185003, 12840573],
    },
    {
        "title": "Popular in Romance",
        "description": "Love stories that are capturing readers' hearts",
        "display_type": "CAROUSEL",
        "works": ["OL34098405W", "OL18020194W", "OL28744393W", "OL37893942W",
                  "OL27733867W", "OL20090688W"],
        "covers": [14630792, 8289078, 13588136, 14818902, 13157661, 14604829],
    },
    # Filled from the fetched catalog (top works for these subjects).
    {"title": "Fantasy Worlds", "description": "Epic quests, magic and dragons",
     "display_type": "CAROUSEL", "from_subject": "subject:fantasy"},
    {"title": "Edge-of-Your-Seat Thrillers", "description": "Mysteries and thrillers you won't put down",
     "display_type": "CAROUSEL", "from_subject": "subject:thrillers"},
    {"title": "Timeless Classics", "description": "The books everyone should read once",
     "display_type": "CAROUSEL", "from_subject": "subject:classic_literature"},
]
FEATURED_SUBJECT_SIZE = 10

FORMAT_ORDER = ["Hardcover", "Paperback", "eBook", "Audiobook"]


def get_json(path, params=None, tries=5):
    url = path if path.startswith("http") else OL + path
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
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


def text_of(value):
    if isinstance(value, dict):
        value = value.get("value", "")
    return (value or "").strip() or None


def year_of(date_str):
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", date_str or "")
    return int(m.group(1)) if m else None


def kind_of(physical_format):
    f = (physical_format or "").lower()
    if "hard" in f:
        return "Hardcover"
    if "paper" in f or "mass market" in f:
        return "Paperback"
    if "electronic" in f or "ebook" in f or "e-book" in f or "kindle" in f:
        return "eBook"
    if "audio" in f or "cd" == f.strip():
        return "Audiobook"
    return "Other"


NON_LATIN = re.compile(r"[Ͱ-῿　-￿]")  # Greek, Cyrillic, CJK, etc.


def english_isbn(isbn):
    """ISBN registration groups 0 and 1 are the English-language ones."""
    if len(isbn) == 13:
        return isbn.startswith(("9780", "9781"))
    return isbn[0] in "01"


def pick_editions(entries, want_cover=None):
    """Choose up to MAX_EDITIONS English editions with an ISBN, varied formats."""
    candidates = []
    for e in entries:
        isbn = (e.get("isbn_13") or e.get("isbn_10") or [None])[0]
        if not isbn:
            continue
        isbn = re.sub(r"[^0-9Xx]", "", isbn)
        if len(isbn) not in (10, 13):
            continue
        langs = [l.get("key", "").rsplit("/", 1)[-1] for l in e.get("languages", [])]
        if langs and "eng" not in langs:
            continue
        if not langs and not english_isbn(isbn):
            continue  # no language listed: trust only English-region ISBNs
        if NON_LATIN.search(" ".join(e.get("publishers") or []) + e.get("title", "")):
            continue  # mislabeled foreign edition
        covers = [c for c in e.get("covers", []) if isinstance(c, int) and c > 0]
        candidates.append({
            "isbn": isbn,
            "kind": kind_of(e.get("physical_format")),
            "publisher": ((e.get("publishers") or [None])[0] or None),
            "year": year_of(e.get("publish_date")),
            "language": "eng",
            "pages": e.get("number_of_pages") if isinstance(e.get("number_of_pages"), int) else None,
            "covers": covers[:2],
            "_has_lang": bool(langs),
        })

    chosen, seen_isbn = [], set()

    def take(c):
        if c["isbn"] not in seen_isbn and len(chosen) < MAX_EDITIONS:
            chosen.append(c)
            seen_isbn.add(c["isbn"])

    # The edition behind the Discover cover goes first so its cover matches.
    if want_cover:
        for c in candidates:
            if want_cover in c["covers"]:
                take(c)
                break

    def score(c):
        return (bool(c["covers"]), c["_has_lang"], bool(c["pages"]), bool(c["publisher"]))

    ranked = sorted(candidates, key=score, reverse=True)
    for fmt in FORMAT_ORDER:  # one per format first
        for c in ranked:
            if c["kind"] == fmt and not any(x["kind"] == fmt for x in chosen):
                take(c)
                break
    for c in ranked:  # then fill with the best remaining
        take(c)

    for c in chosen:
        c.pop("_has_lang", None)
    return chosen


class Command(BaseCommand):
    help = "Download the shared seed catalog from Open Library into library/fixtures/seed_books.json"

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=4, help="Parallel requests (be polite)")
        parser.add_argument("--output", default=str(FIXTURE))

    def handle(self, *args, **opts):
        workers = opts["workers"]

        # 1. Which works?
        wanted = {}  # work key -> {"cover": discover cover id or None, "rating": ...}
        by_subject = {}
        for f in FEATURED:
            for w, c in zip(f.get("works", []), f.get("covers", [])):
                wanted[w] = {"cover": c, "rating": None}

        for query, limit in SUBJECTS:
            data = get_json("/search.json", {
                "q": query, "sort": "readinglog", "limit": limit * 2, "language": "eng",
                "fields": "key,title,ratings_average,author_key",
            }) or {}
            keys = []
            for doc in data.get("docs", []):
                if not doc.get("author_key"):
                    continue
                key = doc["key"].rsplit("/", 1)[-1]
                keys.append(key)
                wanted.setdefault(key, {"cover": None, "rating": None})
                if doc.get("ratings_average"):
                    wanted[key]["rating"] = doc["ratings_average"]
                if len(keys) >= limit:
                    break
            by_subject[query] = keys
            self.stdout.write(f"{query}: {len(keys)} works")

        self.stdout.write(f"{len(wanted)} unique works; fetching details...")

        # 2. Work details + editions.
        def fetch_work(key):
            work = get_json(f"/works/{key}.json")
            if not work:
                return None
            eds = get_json(f"/works/{key}/editions.json", {"limit": 300}) or {}
            rating = wanted[key]["rating"]
            if rating is None:
                r = get_json(f"/works/{key}/ratings.json") or {}
                rating = (r.get("summary") or {}).get("average")
            subjects = []
            for field in ("subjects", "subject_places", "subject_times"):
                subjects += [s if isinstance(s, str) else s.get("name", "") for s in work.get(field, [])]
            editions = pick_editions(eds.get("entries", []), wanted[key]["cover"])
            author_keys = []
            for a in work.get("authors", []):
                k = (a.get("author") or {}).get("key", "")
                if k:
                    author_keys.append(k.rsplit("/", 1)[-1])
            years = [e["year"] for e in editions if e["year"]]
            year = year_of(work.get("first_publish_date")) or (min(years) if years else None)
            if not year:
                all_years = [year_of(e.get("publish_date")) for e in eds.get("entries", [])]
                all_years = [y for y in all_years if y]
                year = min(all_years) if all_years else None
            return {
                "work": key,
                "title": work.get("title", "")[:255],
                "summary": text_of(work.get("description")),
                "year": year,
                "rating": round(float(rating), 2) if rating else None,
                "authors": list(dict.fromkeys(author_keys))[:MAX_AUTHORS_PER_BOOK],
                "genres": sorted(extract_genres_from_subjects(subjects)),
                "editions": editions,
            }

        books, done = [], 0
        with ThreadPoolExecutor(workers) as pool:
            for result in pool.map(fetch_work, list(wanted)):
                done += 1
                if result and result["editions"] and result["authors"]:
                    books.append(result)
                if done % 25 == 0:
                    self.stdout.write(f"  {done}/{len(wanted)} works")

        # 3. Authors.
        author_keys = sorted({a for b in books for a in b["authors"]})
        self.stdout.write(f"Fetching {len(author_keys)} authors...")

        def fetch_author(key):
            a = get_json(f"/authors/{key}.json") or {}
            photos = [p for p in a.get("photos", []) if isinstance(p, int) and p > 0]
            return key, {
                "name": (a.get("name") or a.get("personal_name") or "Unknown Author")[:250],
                "bio": text_of(a.get("bio")),
                "image": f"https://covers.openlibrary.org/a/id/{photos[0]}-L.jpg" if photos else None,
            }

        with ThreadPoolExecutor(workers) as pool:
            authors = dict(pool.map(fetch_author, author_keys))

        # 4. Featured shelves, resolved to works we actually have.
        have = {b["work"] for b in books}
        featured = []
        for f in FEATURED:
            works = f.get("works") or by_subject.get(f.get("from_subject"), [])
            works = [w for w in works if w in have]
            if "from_subject" in f:
                works = works[:FEATURED_SUBJECT_SIZE]
            featured.append({k: f[k] for k in ("title", "description", "display_type")} | {"works": works})

        missing = [w for f in FEATURED for w in f.get("works", []) if w not in have]
        if missing:
            self.stdout.write(self.style.WARNING(f"Discover books without usable editions: {missing}"))

        books.sort(key=lambda b: b["title"].lower())
        out = Path(opts["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "source": "Open Library (openlibrary.org), CC0/ODbL data",
            "generated": date.today().isoformat(),
            "authors": authors,
            "books": books,
            "featured": featured,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

        n_ed = sum(len(b["editions"]) for b in books)
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(books)} books, {n_ed} editions, {len(authors)} authors to {out}"))
