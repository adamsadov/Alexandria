# backend/library/utils/wikipedia_utils.py
import logging
import time
from typing import Optional

import requests

from library.utils.publication_year import USER_AGENT

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
# Wikipedia rejects requests without a User-Agent (HTTP 403).
HEADERS = {"User-Agent": USER_AGENT}
RETRY_STATUSES = (429, 500, 502, 503, 504)


def wikipedia_get(params, tries=4, timeout=10):
    """
    GET the Wikipedia API, waiting and retrying when it rate-limits us (429)
    or is briefly down. Returns the last Response, or None if it never answered.
    """
    response = None
    for attempt in range(tries):
        try:
            response = requests.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=timeout)
        except requests.RequestException:
            response = None
        else:
            if response.status_code not in RETRY_STATUSES:
                return response
        if attempt < tries - 1:
            retry_after = response.headers.get("Retry-After", "") if response is not None else ""
            time.sleep(int(retry_after) if retry_after.isdigit() else 2 ** attempt * 5)
    return response


def get_wikipedia_image_for_author(author_name: str) -> Optional[str]:
    """
    Attempts to find an image for an author using the Wikipedia API.
    
    Args:
        author_name: The name of the author to search for
        
    Returns:
        URL of the author's image if found, None otherwise
    """
    if not author_name or author_name == "Unknown Author":
        return None
        
    try:
        params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "titles": author_name,
            "piprop": "original",
            "pilimit": 1,
            "redirects": 1
        }
        
        response = wikipedia_get(params)
        if response is None or response.status_code != 200:
            return None
            
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        # Get the first page
        if pages:
            page_id = next(iter(pages))
            page = pages[page_id]
            if "original" in page:
                return page["original"]["source"].split("?")[0]  # drop utm_ tracking params
                
        return None
        
    except Exception:
        # Silently fail 
        return None