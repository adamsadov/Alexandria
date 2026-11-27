"""
Import books from Open Library with all of their editions.

    python manage.py import_book "The Hobbit" "Dune"      # top search result per title
    python manage.py import_book --work-id OL893414W       # an exact Open Library work
    python manage.py import_book --file books.txt          # one title per line

Each book is fetched (work, authors, every edition) and written in its own
transaction, so a failure leaves nothing half-imported and doesn't stop the rest
of a batch. Re-importing a book adds editions it doesn't have yet.
"""
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from library.book_upload.openlibrary_fetcher import fetch_work
from library.book_upload.openlibrary_uploader import import_work

PAUSE_BETWEEN_BOOKS = 2  # seconds; be polite to Open Library


class Command(BaseCommand):
    help = "Import books (and all their editions) from Open Library by title or work id"

    def add_arguments(self, parser):
        parser.add_argument("titles", nargs="*", help="Book titles to search for")
        parser.add_argument("--work-id", action="append", default=[], dest="work_ids",
                            help="Open Library work id, e.g. OL893414W (repeatable)")
        parser.add_argument("--file", help="Text file with one title per line")

    def handle(self, *args, **opts):
        jobs = [("work", w) for w in opts["work_ids"]] + [("title", t) for t in opts["titles"]]
        if opts["file"]:
            path = Path(opts["file"])
            if not path.exists():
                raise CommandError(f"File not found: {path}")
            jobs += [("title", line.strip()) for line in path.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
        if not jobs:
            raise CommandError("Give at least one title, --work-id or --file")

        imported, failed = [], []
        for i, (kind, value) in enumerate(jobs, 1):
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n[{i}/{len(jobs)}] {value}"))
            try:
                data = fetch_work(work_id=value) if kind == "work" else fetch_work(title=value)
                book = import_work(data)
            except Exception as e:  # one bad book shouldn't stop a batch
                failed.append(value)
                self.stderr.write(self.style.ERROR(f"Failed: {value}: {e}"))
            else:
                imported.append(value)
                self.stdout.write(self.style.SUCCESS(
                    f"Imported {book.title} ({book.book_id}): {book.editions.count()} editions"))
            if i < len(jobs):
                time.sleep(PAUSE_BETWEEN_BOOKS)

        self.stdout.write(f"\n{len(imported)} imported, {len(failed)} failed")
        if failed:
            self.stdout.write("Failed: " + "; ".join(failed))
            if not imported:
                raise CommandError("Nothing was imported")
