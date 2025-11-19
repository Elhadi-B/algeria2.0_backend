"""
Django settings for pitching_day project.
"""

from pathlib import Path
import os
import environ
import dj_database_url


CSRF_TRUSTED_ORIGINS = [
    "https://jury.algeria20.com",
]


# -------------------------------------------------
# Paths / base dir
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# -------------------------------------------------
# Core security settings
# -------------------------------------------------

SECRET_KEY = env("SECRET_KEY")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = ["*"]

# -------------------------------------------------
# Applications
# -------------------------------------------------

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "corsheaders",
    "judging",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pitching_day.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pitching_day.wsgi.application"
ASGI_APPLICATION = "pitching_day.asgi.application"

# -------------------------------------------------
# Database (via DATABASE_URL)
# -------------------------------------------------

if env("DATABASE_URL", default=""):
    DATABASES = {
        "default": dj_database_url.config(
            env="DATABASE_URL",
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -------------------------------------------------
# Password validation
# -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# -------------------------------------------------
# Internationalization
# -------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------
# Static & media files
# -------------------------------------------------

STATIC_URL = "/api/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/api/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------------------------------
# Default primary key type
# -------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------
# DRF / Spectacular
# -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Pitch Judging API",
    "DESCRIPTION": "REST API for Incubator Pitch Judging Event",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "AUTHENTICATION_WHITELIST": [
        "rest_framework.authentication.SessionAuthentication",
        "judging.authentication.JudgeTokenAuthentication",
    ],
    "SERVERS": [
        {"url": "https://jury.algeria20.com/api", "description": "Production server"},
    ],
    "TAGS": [
        {"name": "Admin", "description": "Admin-only endpoints (require staff authentication)"},
        {"name": "Judge", "description": "Judge endpoints (require token authentication)"},
        {"name": "Teams", "description": "Team management"},
        {"name": "Judges", "description": "Judge management"},
        {"name": "Evaluations", "description": "Score submissions and evaluations"},
    ],
}

# -------------------------------------------------
# CORS / CSRF
# -------------------------------------------------

cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_origins:
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in cors_origins.split(",") if origin.strip()
    ]
else:
    CORS_ALLOWED_ORIGINS = [
        "https://jury.algeria20.com",
        "http://jury.algeria20.com",
    ]

CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    if cors_origins:
        CORS_ALLOW_ALL_ORIGINS = False

CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://jury.algeria20.com,http://jury.algeria20.com",
).split(",")

# CSRF settings for production
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG  # True in production (HTTPS), False in development
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read the cookie
CSRF_USE_SESSIONS = False
CSRF_COOKIE_DOMAIN = None  # Let Django set it automatically
CSRF_COOKIE_NAME = 'csrftoken'  # Default name

# Session cookie settings
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG  # True in production (HTTPS), False in development
SESSION_COOKIE_HTTPONLY = True

# -------------------------------------------------
# Channels
# -------------------------------------------------

REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    (
                        REDIS_URL.split("://")[1]
                        if "://" in REDIS_URL
                        else REDIS_URL
                    )
                ],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# -------------------------------------------------
# Upload limits
# -------------------------------------------------

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
