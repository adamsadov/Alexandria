from rest_framework import serializers
from library.models import Book

class BookSearchSerializer(serializers.ModelSerializer):
    authors = serializers.SerializerMethodField()
    genres = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',          # database id: what club/schedule endpoints expect
            'book_id',     # Open Library work id: used in /book/<book_id> URLs
            'title',
            'summary',
            'year_published',
            'authors',
            'genres',
            'cover_image'
        ]

    def get_authors(self, obj):
        return [author.name for author in obj.authors.all()]

    def get_genres(self, obj):
        return [genre.name for genre in obj.genres.all()]

    def get_cover_image(self, obj):
        # search/catalog.py fetches the cover in the same query as the book
        if hasattr(obj, 'search_cover'):
            return obj.search_cover
        editions = obj.editions.all().prefetch_related('related_edition_image')
        for edition in editions:
            images = edition.related_edition_image.all()
            for image in images:
                if image.is_primary:
                    return image.image_url
        for edition in editions:
            images = edition.related_edition_image.all()
            if images:
                return images[0].image_url
        return None
