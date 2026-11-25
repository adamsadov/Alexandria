from rest_framework.response import Response
from rest_framework.views import APIView

from .catalog import DEFAULT_LIMIT, MAX_LIMIT, search_catalog
from .serializers.book_search_serializer import BookSearchSerializer
from .serializers.author_search_serializer import AuthorSearchSerializer

class SearchBarView(APIView):
    """
    GET /api/search-bar/?q=<text>&limit=<1-50, default 10>&offset=<n>

    {"books": [...], "authors": [...]}, best matches first. The matching and
    ranking live in search/catalog.py (Postgres trigrams with GIN indexes).
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()[:200]
        limit = _int_param(request, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
        offset = _int_param(request, "offset", 0, 0, 10_000)

        if not query:
            return Response({"books": [], "authors": []})

        books, authors = search_catalog(query, limit=limit, offset=offset)
        return Response({
            "books": [{"type": "book", **b} for b in BookSearchSerializer(books, many=True).data],
            "authors": [{"type": "author", **a} for a in AuthorSearchSerializer(authors, many=True).data],
        })


def _int_param(request, name, default, lowest, highest):
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(lowest, min(highest, value))
