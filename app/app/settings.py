"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 4.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def environ_bool(key: str, default=0):
    return bool(int(os.environ.get(key, default)))


def environ_list(key: str, default=""):
    return [
        item.strip() for item in filter(None, os.environ.get(key, default).split(","))
    ]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-changeme")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ_bool("DEBUG", 0)
"""Debug mode implements better logging."""

DEV = environ_bool("DEV") or os.environ.get("DJANGO_ENV", "") == "dev"
"""Dev mode installs additional development packages."""

TESTING = sys.argv[1:2] == ["test"]
NETWORK = os.environ.get("DJANGO_ENV", "dev") == "network"

ALLOWED_HOSTS = []
ALLOWED_HOSTS.extend(environ_list("DJANGO_ALLOWED_HOSTS"))
ALLOWED_HOSTS.extend([os.environ.get("DJANGO_BASE_URL")])

BASE_URL = os.environ.get("DJANGO_BASE_URL", "")
ALLOWED_HOSTS.extend([BASE_URL])

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "core",
    "users",
    "users.authentication",
    "querycsv",
    "analytics",
    "clubs",
    "clubs.polls",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "core.middleware.TimezoneMiddleware",
]

# TODO: Add CORS settings
CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
            os.path.join(BASE_DIR, "core/templates"),
        ],
        # "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                "admin_tools.template_loaders.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASS"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

# TIME_ZONE = "America/New_York" # TODO: UTC
TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

STATIC_URL = "/static/static/"
MEDIA_URL = "/static/media/"

# MEDIA_ROOT = "/vol/web/media"
# STATIC_ROOT = "/vol/web/static"
MEDIA_ROOT = "/vol/static/media"
STATIC_ROOT = "/vol/static/static"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django Rest Framework
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.views.api_exception_handler",
}


SPECTACULAR_SETTINGS = {
    "TITLE": "OSC Member Manager API",
    "DESCRIPTION": "Some cool app to manage users or something.",
    "VERSION": "1.0.0",
}


###############################
# == Auth & Session Config == #
###############################

# Allows handling csrf and session cookies in external requests
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# Prevent csrf and session cookies from being set by JS
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = False

# Only allow cookies from these origins
CSRF_TRUSTED_ORIGINS = environ_list("CSRF_TRUSTED_ORIGINS")
CSRF_TRUSTED_ORIGINS.extend([BASE_URL])

# Only allow cookies to be sent over HTTPS
CSRF_COOKIE_SECURE = environ_bool("CSRF_COOKIE_SECURE", True)
SESSION_COOKIE_SECURE = environ_bool("SESSION_COOKIE_SECURE", True)

# CORS Settings
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]
CORS_ALLOW_CREDENTIALS = True

# Other auth settings
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/auth/login/"
AUTHENTICATION_BACKENDS = ["core.backend.CustomBackend"]


########################
# ==  AWS S3 Config == #
########################
S3_STORAGE_BACKEND = bool(int(os.environ.get("S3_STORAGE_BACKEND", 1)))
if S3_STORAGE_BACKEND is True:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

AWS_DEFAULT_ACL = "public-read"
AWS_STORAGE_BUCKET_NAME = os.environ.get("S3_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = os.environ.get("S3_STORAGE_BUCKET_REGION", "us-east-1")
AWS_QUERYSTRING_AUTH = False

######################
# == Email Config == #
######################
CONSOLE_EMAIL_BACKEND = environ_bool("CONSOLE_EMAIL_BACKEND", 0)

if CONSOLE_EMAIL_BACKEND:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", None)

EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "admin@example.com")

#######################
# == Celery Config == #
#######################
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND")
CELERY_TASK_ACKS_LATE = bool(int(os.environ.get("CELERY_TASK_ACKS_LATE", "1")))
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = bool(
    int(os.environ.get("CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", "1"))
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Custom schedules
CELERY_BEAT_SCHEDULE = {}

###############################
# == Environment Overrides == #
###############################

if DEV:
    import socket

    INSTALLED_APPS.append("django_browser_reload")
    INSTALLED_APPS.append("debug_toolbar")
    INSTALLED_APPS.append("django_extensions")

    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")
    CSRF_TRUSTED_ORIGINS.extend(["http://0.0.0.0"])

    INTERNAL_IPS = [
        "127.0.0.1",
        "10.0.2.2",
    ]
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend(["http://0.0.0.0"])


if TESTING:
    # Ensure tasks execute immediately
    CELERY_TASK_ALWAYS_EAGER = True

    # Force disable notifications
    EMAIL_HOST_PASSWORD = None

if DEV or TESTING:
    # Allow for migrations during dev mode
    INSTALLED_APPS.append("core.mock")
