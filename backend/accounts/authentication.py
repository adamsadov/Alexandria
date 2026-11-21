from rest_framework.authentication import SessionAuthentication


class SessionAuthentication401(SessionAuthentication):
    """
    Session (cookie) auth that answers unauthenticated requests with 401
    instead of DRF's default 403, so the frontend can tell
    "please log in" (401) apart from "not allowed" (403).
    """

    def authenticate_header(self, request):
        return 'Session realm="api"'
