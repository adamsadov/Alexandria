"""
Merge authors that are the same person split across Open Library records.

    python manage.py merge_authors --dry-run   # list what would merge
    python manage.py merge_authors             # merge

Authors are grouped by normalized name ("J.R.R. Tolkien" = "J. R. R. Tolkien").
A name match alone never merges: each pair must share a book here, or
library.utils.authors.same_person() must confirm it on Open Library (same
Wikidata id, or work titles in common, with no conflicting dates). The author
with the most books is kept; the others' book links and OL keys move to it.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from library.models import Author
from library.utils.authors import (
    author_keys, get_author_record, merge_into, normalize_name, same_person,
)
from library.utils.publication_year import get_json


class Command(BaseCommand):
    help = "Merge duplicate authors (same person, several Open Library records)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List merges without changing anything")

    def handle(self, *args, **opts):
        self.fetch = get_json
        self.dry_run = dry_run = opts["dry_run"]

        groups = defaultdict(list)
        for author in Author.objects.annotate(book_count=Count("related_author_books")):
            groups[normalize_name(author.name)].append(author)
        groups = {name: authors for name, authors in groups.items() if name and len(authors) > 1}
        self.stdout.write(f"{len(groups)} name(s) shared by more than one author")

        merged = skipped = 0
        for authors in groups.values():
            for keeper, dupes, reasons in self._clusters(authors):
                titles = ", ".join(f"{d.name} [{d.author_id[:10]}] ({reasons[d.pk]})" for d in dupes)
                self.stdout.write(f"  keep {keeper.name} [{keeper.author_id[:10]}, {keeper.book_count} books] "
                                  f"<- {titles}")
                if not dry_run:
                    merge_into(keeper, dupes)
                merged += len(dupes)
            for a, b, reason in self._unconfirmed:
                self.stdout.write(self.style.WARNING(
                    f"  not merged: {a.name} [{a.author_id[:10]}] / {b.name} [{b.author_id[:10]}]: {reason}"))
                skipped += 1

        verb = "Would merge" if dry_run else "Merged"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {merged} duplicate author(s); {skipped} same-name pair(s) left apart."))

    def _clusters(self, authors):
        """Union-find over confirmed pairs. Yields (keeper, duplicates, reason per duplicate)."""
        self._unconfirmed = []
        keys = {a.pk: author_keys(a, self.fetch, save=not self.dry_run) for a in authors}
        records = {k: get_author_record(k, self.fetch) for ks in keys.values() for k in ks}
        books = {a.pk: set(a.related_author_books.values_list("book_id", flat=True)) for a in authors}

        parent = {a.pk: a.pk for a in authors}

        def root(pk):
            while parent[pk] != pk:
                parent[pk] = parent[parent[pk]]
                pk = parent[pk]
            return pk

        reasons = {}
        for i, a in enumerate(authors):
            for b in authors[i + 1:]:
                match, reason = self._compare(a, b, keys, records, books)
                if match:
                    parent[root(b.pk)] = root(a.pk)
                    reasons[(a.pk, b.pk)] = reasons[(b.pk, a.pk)] = reason
                else:
                    self._unconfirmed.append((a, b, reason))

        clusters = defaultdict(list)
        for a in authors:
            clusters[root(a.pk)].append(a)
        # Pairs that ended up joined through a third record aren't "unconfirmed".
        self._unconfirmed = [(a, b, r) for a, b, r in self._unconfirmed if root(a.pk) != root(b.pk)]

        for members in clusters.values():
            if len(members) < 2:
                continue
            # Most books; on a tie, the fuller Open Library record (dates, Wikidata), not a stub.
            def rank(a):
                recs = [records.get(k) or {} for k in keys[a.pk]]
                known = max((sum(bool(r.get(f)) for f in ("birth_date", "death_date", "remote_ids", "bio"))
                             for r in recs), default=0)
                return (a.book_count, known, bool(a.biography), -a.pk)
            keeper = max(members, key=rank)
            dupes = [a for a in members if a.pk != keeper.pk]
            why = {}
            for d in dupes:
                why[d.pk] = reasons.get((keeper.pk, d.pk)) or next(
                    (reasons[(m.pk, d.pk)] for m in members if (m.pk, d.pk) in reasons), "linked via another record")
            yield keeper, dupes, why

    def _compare(self, a, b, keys, records, books):
        if books[a.pk] & books[b.pk]:
            return True, "share a book"
        if not keys[a.pk] or not keys[b.pk]:
            return False, "Open Library key unknown"
        for ka in keys[a.pk]:
            for kb in keys[b.pk]:
                match, reason = same_person(ka, kb, self.fetch, records=records)
                if match:
                    return True, reason
        return False, reason
