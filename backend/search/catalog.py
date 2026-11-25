"""
Catalog search: fast, typo-tolerant, ranked, over the live database.

Uses Postgres trigrams (pg_trgm) with GIN indexes on Book.title and
Author.name (library migration 0003), so a search looks up the index
instead of scanning every row, and "hary poter" still finds Harry Potter.

How a book matches the query q:
  * its title is word-similar to q (``q <% title``: q is close to some run
    of words in the title; this also covers substrings, "otter" -> Potter); or
  * one of its authors' names is word-similar to q ("tolkien" -> Tolkien's
    books); or
  * q is an ISBN (10 or 13 digits, dashes/spaces ignored) of one of its
    editions, matched exactly through the unique ISBN index.

How books are ordered:
  1. ISBN match
  2. exact title, then title starting with q
  3. similarity score: word similarity + whole-string similarity (the
     second breaks ties toward closer, shorter matches), using the title
     or, slightly discounted, the best-matching author
  4. average rating, then title

Queries shorter than 3 characters can't form trigrams, so they match by
prefix only.

Speed: each way of matching is its own indexed lookup (GIN trigram index on
title, on author name, unique index on ISBN), combined with UNION. Joining
them with OR in one WHERE clause, or using icontains (Django's
UPPER(..) LIKE, which the trigram index can't serve), makes Postgres scan
the whole table instead.
"""
import re

from django.contrib.postgres.search import TrigramSimilarity, TrigramWordSimilarity
from django.db import connection, transaction
from django.db.models import (
    Case, F, FloatField, IntegerField, OuterRef, Q, Subquery, Value, When,
)
from django.db.models.functions import Coalesce, Greatest

from library.models import Author, Book, BookAuthor, CoverImage, Edition

# word_similarity cutoff for a match. Measured on the catalog: real matches
# score >= 0.5 ("hary poter" -> Harry Potter 0.60, "tolkein" -> Tolkien 0.50),
# near misses below ("hunger games" -> The Inheritance Games 0.46).
WORD_SIMILARITY_THRESHOLD = 0.5
# An author-name match ranks a little below an equally good title match.
AUTHOR_WEIGHT = 0.9
# At most this many books per kind of match (title / author) get scored.
# Normal queries match far fewer; a near-universal one like "the" matches
# most of the catalog, and scoring all of it would take seconds.
MAX_CANDIDATES = 1000
MIN_TRIGRAM_LENGTH = 3

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def clean_isbn(query):
    """The query as a bare ISBN-10/13 ("978-0-441-01359-3" -> "9780441013593"), or None."""
    digits = re.sub(r"[\s-]", "", query).upper()
    if re.fullmatch(r"\d{13}|\d{9}[\dX]", digits):
        return digits
    return None


def isbn_variants(isbn):
    """An ISBN plus its 10/13-digit twin, since editions store either form."""
    variants = {isbn}
    if len(isbn) == 10:
        core = "978" + isbn[:9]
        total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(core))
        variants.add(core + str((10 - total % 10) % 10))
    elif isbn.startswith("978"):
        core = isbn[3:12]
        total = sum(int(d) * (10 - i) for i, d in enumerate(core))
        check = (11 - total % 11) % 11
        variants.add(core + ("X" if check == 10 else str(check)))
    return variants


def _set_threshold():
    """Use our cutoff for `<%` (word similarity) for the rest of this transaction."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('pg_trgm.word_similarity_threshold', %s, true)",
            [str(WORD_SIMILARITY_THRESHOLD)],
        )


def _cover_subquery():
    """The book's cover: its primary edition's primary image, else the best one we have."""
    return Subquery(
        CoverImage.objects.filter(edition__book=OuterRef("pk"))
        .order_by("-edition__is_primary", "-is_primary", "id")
        .values("image_url")[:1]
    )


def book_queryset(query):
    """
    All books matching ``query``, best first (unsliced, so it can be paged or
    EXPLAINed). Evaluate it inside a transaction after _set_threshold();
    search_catalog does both.
    """
    isbn = clean_isbn(query)
    isbn_book_ids = []
    if isbn:
        isbn_book_ids = list(
            Edition.objects.filter(isbn__in=isbn_variants(isbn)).values_list("book_id", flat=True)
        )

    if len(query) < MIN_TRIGRAM_LENGTH:
        by_title = Book.objects.filter(title__istartswith=query)
        authors = Author.objects.filter(name__istartswith=query)
    else:
        by_title = Book.objects.filter(title__trigram_word_similar=query)
        authors = Author.objects.filter(name__trigram_word_similar=query)
    # order_by() clears Book's default ordering, which would otherwise sort
    # every candidate by title before the cap.
    candidate_ids = by_title.order_by().values("pk")[:MAX_CANDIDATES].union(
        BookAuthor.objects.filter(author__in=authors.order_by().values("pk"))
        .order_by().values("book_id")[:MAX_CANDIDATES],
        Book.objects.filter(pk__in=isbn_book_ids).order_by().values("pk"),
    )
    books = Book.objects.filter(pk__in=candidate_ids)

    best_author_score = Subquery(
        BookAuthor.objects.filter(book=OuterRef("pk"))
        .annotate(score=TrigramWordSimilarity(query, "author__name")
                  + TrigramSimilarity("author__name", query))
        .order_by("-score")
        .values("score")[:1],
        output_field=FloatField(),
    )

    return (
        books.annotate(
            tier=Case(
                When(pk__in=isbn_book_ids, then=Value(0)),
                When(title__iexact=query, then=Value(1)),
                When(title__istartswith=query, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            score=Greatest(
                TrigramWordSimilarity(query, "title") + TrigramSimilarity("title", query),
                Coalesce(best_author_score, Value(0.0)) * AUTHOR_WEIGHT,
                output_field=FloatField(),
            ),
            search_cover=_cover_subquery(),
        )
        .order_by("tier", F("score").desc(), F("average_rating").desc(nulls_last=True), "title")
        .prefetch_related("authors", "genres")
    )


def search_books(query, limit=DEFAULT_LIMIT, offset=0):
    """A page of books matching ``query``, best first."""
    return list(book_queryset(query)[offset:offset + limit])


def author_queryset(query):
    """All authors whose names match ``query``, best first."""
    if len(query) < MIN_TRIGRAM_LENGTH:
        authors = Author.objects.filter(name__istartswith=query).annotate(score=Value(1.0))
    else:
        authors = Author.objects.filter(name__trigram_word_similar=query).annotate(score=TrigramWordSimilarity(query, "name") + TrigramSimilarity("name", query))
    return authors.order_by(F("score").desc(), "name")


def search_authors(query, limit=DEFAULT_LIMIT, offset=0):
    """A page of authors whose names match ``query``, best first."""
    return list(author_queryset(query)[offset:offset + limit])


def search_catalog(query, limit=DEFAULT_LIMIT, offset=0):
    """(books, authors) matching ``query``."""
    with transaction.atomic():
        _set_threshold()
        return search_books(query, limit, offset), search_authors(query, limit, offset)
