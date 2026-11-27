"""
Write one Open Library work (fetched by openlibrary_fetcher.fetch_work) into the
database: its authors, the book, its genres, and every edition with an ISBN.

Used by `manage.py import_book`.
"""
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction

from library.models import (
    Book, Author, BookAuthor, Genre, BookGenre,
    Edition, Publisher, CoverImage
)
from library.utils.authors import resolve_author
from library.utils.genre_utils import extract_genres_from_subjects, get_primary_genre
from library.utils.publication_year import parse_edition_year, parse_year, pick_first_year
from library.utils.wikipedia_utils import get_wikipedia_image_for_author


class LibraryUpload:
    """Uploads book data from local JSON files into database.."""
    
    def __init__(self, work_data: Dict[str, Any], editions_data: List[Dict[str, Any]],
                 authors_data: List[Dict[str, Any]]):
        """
        Args:
            work_data: the Open Library work record
            editions_data: its edition records
            authors_data: its author records
        """
        self.work_data = work_data
        self.editions_data = editions_data or []
        self.authors_data = authors_data or []

    def _get_or_create_publisher(self, name: str) -> Publisher:
        """Get or create a Publisher object."""
        if not name:
            return None
        
        publisher, created = Publisher.objects.get_or_create(
            name=name[:100] 
        )
        
        if created:
            print(f"Created new publisher: {name}")
        
        return publisher
    
    def _get_or_create_genre(self, name: str) -> Genre:
        """Get or create a Genre object."""
        if not name:
            return None
        
        genre, created = Genre.objects.get_or_create(
            name=name[:100]  
        )
        
        if created:
            print(f"Created new genre: {name}")
        
        return genre
    
    
    @transaction.atomic
    def upload_authors(self) -> Dict[str, Author]:
        """
        Upload authors to the database.
        
        Returns:
            Dictionary mapping Open Library author keys to Author objects
        """
        author_map = {}
        
        for author_data in self.authors_data:
            bio = author_data.get('bio', '')
            
            # Handle different forms of biography field
            if isinstance(bio, dict):
                bio = bio.get('value', '')
            
            # Follows Open Library redirects and links known duplicate records
            # (another OL key for the same person) to the existing author.
            author, created = resolve_author(author_data, defaults={'biography': bio})
            key = author_data.get('key', '').replace('/authors/', '')
            
            if created:
                # Try to get Wikipedia image, but don't let failure disrupt the process
                author_image = None
                try:
                    author_image = get_wikipedia_image_for_author(author.name)
                except Exception as e:
                    print(f"Note: Could not fetch Wikipedia image for {author.name}: {e}")
                # If no Wikipedia image, use a default placeholder
                author.author_image = author_image or "https://via.placeholder.com/150?text=Author"
                author.save(update_fields=['author_image'])
                print(f"Created new author: {author.name}")
            else:
                print(f"Using existing author: {author.name}")
            
            author_map[f"/authors/{key}"] = author
        
        return author_map
    
    @transaction.atomic
    def upload_book_and_genres(self, author_map: Dict[str, Author]) -> Book:
        """
        Upload a book and its genres to the database.
        
        Args:
            author_map: Dictionary mapping Open Library author keys to Author objects
            
        Returns:
            The created Book object
        """
        # Extract book details
        title = self.work_data.get('title', 'Unknown Title')
        key = self.work_data.get('key', '').replace('/works/', '')
        book_id = key  # Use the work ID as the unique hash
        
        # Get description
        description = self.work_data.get('description', '')
        if isinstance(description, dict):
            description = description.get('value', '')
        
        # Original publication year: what the fetcher looked up on Open Library
        # (see library/utils/publication_year.py), else the same rule applied
        # to the editions we downloaded. Unknown stays None, never a made-up year.
        year_published = parse_year(self.work_data.get('first_publish_year')) or pick_first_year(
            edition.get('publish_date') for edition in (self.editions_data or []))
        if not year_published:
            print("WARNING: Could not determine publication year from API data")

        # Get original language
        languages = self.work_data.get('original_languages', [])
        original_language = languages[0].get('key', '').replace('/languages/', '') if languages else None
        
        # Create or update the book
        book, created = Book.objects.get_or_create(
            book_id=book_id,
            defaults={
                'title': title[:255],  
                'summary': description,
                'year_published': year_published,
                'original_language': original_language,
                'average_rating': Decimal('0.00') 
            }
        )
        
        # If the book already exists, correct its year when we found one
        if not created and year_published and book.year_published != year_published:
            book.year_published = year_published
            book.save()
            print(f"Updated existing book's publication year: {year_published}")
        
        # Print debugging info
        print(f"Book year_published set to: {year_published}")
        
        if created:
            print(f"Created new book: {title}")
        
        # Link authors to book
        for author_key, author_obj in author_map.items():
            BookAuthor.objects.get_or_create(
                book=book,
                author=author_obj
            )
            print(f"Linked author {author_obj.name} to book {book.title}")
        
        # Extract subjects from different fields
        subjects = []

        # Extract subjects from different fields
        if 'subjects' in self.work_data:
            subjects.extend([s.get('name', s) if isinstance(s, dict) else s 
                           for s in self.work_data['subjects']])

        if 'subject_places' in self.work_data:
            subjects.extend(self.work_data['subject_places'])

        if 'subject_times' in self.work_data:
            subjects.extend(self.work_data['subject_times'])

        # Extract normalized genres using our utility function
        normalized_genres = extract_genres_from_subjects(subjects)
                
        if normalized_genres:
            for genre_name in normalized_genres:
                genre = self._get_or_create_genre(genre_name)
                if genre:
                    BookGenre.objects.get_or_create(
                        book=book,
                        genre=genre
                    )
                    print(f"Added genre {genre.name} to book {book.title}")
        else:
            # Add a default genre if no valid genres were found
            default_genre = self._get_or_create_genre("fiction")
            if default_genre:
                BookGenre.objects.get_or_create(
                    book=book,
                    genre=default_genre
                )
                print(f"Added default genre 'fiction' to book {book.title}")
        
        return book
    
    @transaction.atomic
    def upload_editions(self, book: Book) -> None:
        """
        Upload editions for a book to the database.
        
        Args:
            book: The Book object to link editions to
        """
        # Keep track of whether we've set a primary cover yet
        primary_cover_set = False
        
        for edition_data in self.editions_data:

            # Extract edition details
            key = edition_data.get('key', '').replace('/books/', '')
            isbn = edition_data.get('isbn_13', [None])[0] or edition_data.get('isbn_10', [None])[0]
            
            # Skip if no ISBN. We should look at possibly creating our own isbn instead of skipping.
            if not isbn:
                print(f"Skipping edition with no ISBN: {edition_data.get('title', 'Unknown')}")
                continue
            
            # Check if this edition already exists
            if Edition.objects.filter(isbn=isbn).exists():
                print(f"Edition with ISBN {isbn} already exists, skipping")
                continue
            
            # Determine format/kind
            physical_format = edition_data.get('physical_format', '').capitalize()
            if physical_format in ['Hardcover', 'Paperback']:
                kind = physical_format
            elif 'electronic' in physical_format.lower() or 'ebook' in physical_format.lower():
                kind = 'eBook'
            elif 'audio' in physical_format.lower():
                kind = 'Audiobook'
            else:
                kind = 'Other'
            
            # Get publication year
            publish_date = edition_data.get('publish_date')
            # This printing's own year; left blank if unknown, never the book's year
            publication_year = parse_edition_year(publish_date)
            
            # Get publisher
            publisher_name = edition_data.get('publishers', ['Unknown Publisher'])[0]
            publisher = self._get_or_create_publisher(publisher_name)
            
            # Get language
            languages = edition_data.get('languages', [])
            language_code = languages[0].get('key', '').replace('/languages/', '') if languages else 'eng'
            
            # Create the edition
            edition = Edition.objects.create(
                book=book,
                isbn=isbn[:13],  
                publisher=publisher,
                kind=kind,
                publication_year=publication_year,
                language=language_code[:50], 
                page_count=edition_data.get('number_of_pages'),
                edition_number=edition_data.get('edition_number', 1),
                abridged=False  # Default value
            )
            
            print(f"Created edition: {edition}")
            
            # Add cover images
            covers = edition_data.get('covers', [])
            for i, cover_id in enumerate(covers):
                # Only set the first cover of the first edition as primary
                is_primary = (not primary_cover_set) and (i == 0)
                
                CoverImage.objects.create(
                    edition=edition,
                    image_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
                    is_primary=is_primary
                )
                
                # If we just set a primary cover, update our flag
                if is_primary:
                    primary_cover_set = True
                    
                print(f"Added cover image for edition {edition}")
    
    def upload_all(self) -> Book:
        """Upload all data to the database."""
        # Upload authors
        author_map = self.upload_authors()
        
        # Upload the book and genres
        book = self.upload_book_and_genres(author_map)
        
        # Upload editions
        self.upload_editions(book)
        
        print(f"Successfully uploaded all data for: {book.title}")
        return book

def import_work(data: Dict[str, Any]) -> Book:
    """Upload fetch_work()'s result in one transaction (all or nothing). Returns the Book."""
    uploader = LibraryUpload(data["work"], data["editions"], data["authors"])
    with transaction.atomic():
        return uploader.upload_all()
