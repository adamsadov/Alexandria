from django.urls import path

from .views import (
    CsrfCookieView,
    UserBookClubsView,
    UserBookProgressView,
    UserCurrentlyReadingView,
    UserDeleteView,
    UserProfilePictureUpdateView,
    UserProfileUpdateView,
    UserProfileView,
    UserPublicProfileView,
)

# Login, sign-up, logout, email verification and password reset are served
# by django-allauth under /_allauth/browser/v1/ (see config/urls.py).

app_name = 'accounts'

urlpatterns = [
    # Sets the csrftoken cookie for the frontend
    path('csrf/', CsrfCookieView.as_view(), name='csrf'),

    # User profile update
    path('user/profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),

    # User profile pic upload
    path('user/profile/update-picture/', UserProfilePictureUpdateView.as_view(), name='update-profile-picture'),

    # User profile delete
    path('user/delete', UserDeleteView.as_view(), name='user-delete'),

    # User profiles
    path("users/<int:pk>/", UserPublicProfileView.as_view(), name="user-public-profile"),
    path('profile/', UserProfileView.as_view(), name='profile'),

    # Checking user books progress
    path('books/<str:book_id>/progress/', UserBookProgressView.as_view(), name='book-progress'),

    # using query parameters instead of URL path segments
    path('users/currently-reading/', UserCurrentlyReadingView.as_view(), name='user-currently-reading'),
    path('users/book-clubs/', UserBookClubsView.as_view(), name='user-book-clubs'),
]
