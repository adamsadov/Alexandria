"""
One Alexandria author per person, even when Open Library has several records.

Open Library is crowd-edited, and the same person often has more than one
author record (George Orwell is OL118077A on Animal Farm and OL15318546A on
Nineteen Eighty-Four). This module decides when two records are the same
person and finds the Author an importer should link to.

    resolve_author(record)   importers: the Author for an OL author record
    same_person(a, b)        are two OL author keys the same person?
    merge_into(keeper, dupes)  move duplicates' books and keys to one Author

`fetch` is any callable shaped like publication_year.get_json (path -> dict
or None); tests pass a stub so nothing touches the network.
"""
import hashlib
import re
import unicodedata

from django.db import transaction

from library.models import Author, AuthorKey, BookAuthor
from library.utils.publication_year import get_json

MAX_REDIRECTS = 5
WORKS_LIMIT = 1000          # titles fetched per author when comparing records
KEY_RECOVERY_BOOKS = 3      # books checked to recover a legacy author's OL key
PLACEHOLDER_IMAGE = "placeholder.com"


# ------------------------------------------------------------------ helpers
def bare_key(key):
    """'/authors/OL118077A' or 'OL118077A' -> 'OL118077A'."""
    return (key or "").rstrip("/").rsplit("/", 1)[-1]


def author_hash(key):
    """Author.author_id for an OL key. Same scheme as both importers have always used."""
    return hashlib.sha256(bare_key(key).encode("utf-8")).hexdigest()


def normalize_name(name):
    """
    Compare names ignoring case, accents, punctuation and spacing in initials:
    "J.R.R. Tolkien", "J. R. R. Tolkien" and "JRR Tolkien" -> "jrr tolkien".
    """
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    tokens, initials = [], ""
    for token in re.findall(r"[a-z0-9]+", text):
        if len(token) == 1:
            initials += token
            continue
        if initials:
            tokens.append(initials)
            initials = ""
        tokens.append(token)
    if initials:
        tokens.append(initials)
    return " ".join(tokens)


def _title(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _year(value):
    match = re.search(r"\b(\d{4})\b", value or "")
    return match.group(1) if match else None


def _wikidata(record):
    return (record.get("remote_ids") or {}).get("wikidata")


def _is_placeholder(url):
    return not url or PLACEHOLDER_IMAGE in url


# ---------------------------------------------------------- Open Library side
def follow_redirects(record, fetch=get_json):
    """
    Open Library turns a merged-away record into
    {"type": {"key": "/type/redirect"}, "location": "/authors/OL…A"}.
    Follow it to the record it points to. None if the chain breaks or loops.
    """
    seen = set()
    for _ in range(MAX_REDIRECTS + 1):
        if not record:
            return None
        if (record.get("type") or {}).get("key") != "/type/redirect":
            return record
        location = record.get("location")
        if not location or location in seen:
            return None
        seen.add(location)
        record = fetch(f"{location}.json")
    return None


def get_author_record(key, fetch=get_json):
    """The live OL record for a key, after redirects (None if unavailable)."""
    return follow_redirects(fetch(f"/authors/{bare_key(key)}.json"), fetch)


def _work_titles(key, fetch):
    data = fetch(f"/authors/{bare_key(key)}/works.json?limit={WORKS_LIMIT}") or {}
    return {_title(e.get("title")) for e in data.get("entries", [])} - {""}


def same_person(key_a, key_b, fetch=get_json, records=None):
    """
    Two OL author records with the same name are the same person when the
    evidence says so, never on the name alone:

      - different Wikidata ids or different birth/death years -> no
      - the same Wikidata id -> yes
      - at least one work title in common -> yes

    `records` may hold already-fetched {key: record} to save requests.
    Returns (bool, reason).
    """
    records = records or {}
    a = records.get(key_a) or get_author_record(key_a, fetch) or {}
    b = records.get(key_b) or get_author_record(key_b, fetch) or {}
    if a.get("key") and a.get("key") == b.get("key"):
        return True, "redirects to the same record"

    wa, wb = _wikidata(a), _wikidata(b)
    if wa and wb:
        return (wa == wb), ("same Wikidata id" if wa == wb else "different Wikidata ids")
    for field in ("birth_date", "death_date"):
        ya, yb = _year(a.get(field)), _year(b.get(field))
        if ya and yb and ya != yb:
            return False, f"different {field.replace('_', ' ')}s ({ya} vs {yb})"

    shared = _work_titles(key_a, fetch) & _work_titles(key_b, fetch)
    if shared:
        return True, f"{len(shared)} work title(s) in common"
    return False, "no shared works or identifiers"


# ------------------------------------------------------------ database side
def find_author(key):
    """The Author an OL key already belongs to, or None. No network."""
    key = bare_key(key)
    alias = AuthorKey.objects.select_related("author").filter(key=key).first()
    if alias:
        return alias.author
    return Author.objects.filter(author_id=author_hash(key)).first()


def remember_key(author, key):
    """Record that `key` belongs to `author` (moves it if it pointed elsewhere)."""
    key = bare_key(key)
    if key:
        AuthorKey.objects.update_or_create(key=key, defaults={"author": author})


def author_keys(author, fetch=get_json, save=True):
    """
    Every OL key known for an Author. Authors imported before AuthorKey existed
    only have sha256(key) in author_id, so recover the key by looking up which
    author of their books (book_id is the OL work id) hashes to it. The
    recovered key is stored unless save=False.
    """
    keys = list(author.ol_keys.values_list("key", flat=True))
    if keys:
        return keys
    links = author.related_author_books.select_related("book")[:KEY_RECOVERY_BOOKS]
    for link in links:
        work = fetch(f"/works/{link.book.book_id}.json") or {}
        for entry in work.get("authors", []):
            key = bare_key((entry.get("author") or {}).get("key"))
            if key and author_hash(key) == author.author_id:
                if save:
                    remember_key(author, key)
                return [key]
    return []


def same_name_authors(name, exclude=None):
    """Authors whose normalized name equals `name`'s (indexed trigram prefilter)."""
    target = normalize_name(name)
    if not target:
        return []
    qs = Author.objects.filter(name__trigram_similar=name)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return [a for a in qs if normalize_name(a.name) == target]


def resolve_author(record, fetch=get_json, defaults=None):
    """
    The Author an importer should link for an OL author record:

    1. follow OL redirects to the live record;
    2. a key we already know (its own, or a duplicate merged earlier) -> that Author;
    3. an Author with the same name whom same_person() confirms -> that Author,
       and the new key is remembered for next time;
    4. otherwise a new Author.

    `defaults` are extra fields (biography, author_image) for a new Author.
    Returns (author, created).
    """
    original_key = bare_key((record or {}).get("key"))
    live = follow_redirects(record, fetch) or record or {}
    key = bare_key(live.get("key")) or original_key
    name = (live.get("name") or "Unknown Author")[:250]

    author = find_author(key) or (find_author(original_key) if original_key else None)
    if author:
        remember_key(author, key)
        if original_key and original_key != key:
            remember_key(author, original_key)
        return author, False

    for candidate in same_name_authors(name):
        for candidate_key in author_keys(candidate, fetch):
            match, _reason = same_person(key, candidate_key, fetch, records={key: live})
            if match:
                remember_key(candidate, key)
                return candidate, False

    author = Author.objects.create(author_id=author_hash(key), name=name, **(defaults or {}))
    remember_key(author, key)
    if original_key and original_key != key:
        remember_key(author, original_key)
    return author, True


@transaction.atomic
def merge_into(keeper, duplicates):
    """
    Fold `duplicates` into `keeper`: repoint their book links (dropping any the
    keeper already has), move their OL keys, fill in a missing bio or image,
    then delete them. Returns the number of book links moved.
    """
    moved = 0
    for dupe in duplicates:
        if dupe.pk == keeper.pk:
            continue
        for link in BookAuthor.objects.filter(author=dupe):
            if BookAuthor.objects.filter(author=keeper, book_id=link.book_id).exists():
                link.delete()
            else:
                link.author = keeper
                link.save(update_fields=["author"])
                moved += 1
        AuthorKey.objects.filter(author=dupe).update(author=keeper)
        if not keeper.biography and dupe.biography:
            keeper.biography = dupe.biography
        if _is_placeholder(keeper.author_image) and not _is_placeholder(dupe.author_image):
            keeper.author_image = dupe.author_image
        dupe.delete()
    keeper.save(update_fields=["biography", "author_image"])
    return moved
