"""
Django application settings.
"""
from pathlib import Path
import os
import environ

# Initialize environment variables.
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Load app configurations from env.
SECRET_KEY = env("SECRET_KEY", default="your-default-secret-key")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# Frontend URL
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# The from: ...@some.com like the no-reply
DEFAULT_FROM_EMAIL = env("EMAIL_HOST_USER", default="no-reply@alexandria.local")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # trigram search (pg_trgm)
    'django_filters',
    "mptt",
    "corsheaders",
    "library",
    "entity_pages",
    'rest_framework',
    "allauth",
    "allauth.account",
    "allauth.headless",
    'accounts',
    "search",
    "shelves",
    "discovery",
    "reviews",
    "bookclubs",
    "book"
]

# Set custom user model
AUTH_USER_MODEL = "library.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False # DO NOT SET TO TRUE FOR PRODUCTION
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True

# The frontend proxies /api and /_allauth through Next.js, so the browser's
# Origin is the frontend's. CSRF checks must trust it.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[FRONTEND_URL])

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="alexandria"),
        "USER": env("POSTGRES_USER", default="postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="changeme"),
        "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length" : 8,
        }
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    # adding our password validator.py we created
    
    # {
    #     "NAME": "library.validators.CustomPasswordValidator"
    # },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session security
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = "DENY"

# Logging
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "debug_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django_debug.log"),
            "encoding": "utf-8",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django_errors.log"),
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["debug_file", "error_file"],
            # INFO, not DEBUG: DEBUG logs every SQL query, which floods the file.
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": True,
        },
    },
}

# Email configurations
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="your-email@gmail.com")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="your-email-password")
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER



# Rest framework: API requests are authenticated by the Django session cookie
# that allauth sets at login. SessionAuthentication enforces CSRF on writes.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.SessionAuthentication401',
    ]
}

# ===== Authentication (django-allauth, headless) =====
# Users sign up and log in with email + password. The username starts out
# equal to the email; the frontend's profile-setup modal asks for a real one.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = "accounts.adapter.AccountAdapter"
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="mandatory")
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False

# Only the JSON API; the frontend renders every page.
HEADLESS_ONLY = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{FRONTEND_URL}/auth/verify-email/{{key}}",
    "account_reset_password": f"{FRONTEND_URL}/auth/forgot-password",
    "account_reset_password_from_key": f"{FRONTEND_URL}/auth/reset-password/{{key}}",
    "account_signup": f"{FRONTEND_URL}/auth/sign-up",
}

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # two weeks