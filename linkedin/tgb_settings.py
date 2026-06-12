# linkedin/tgb_settings.py
"""TGB Hunt Django settings."""
import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# Data directory: env var wins, otherwise next to executable (frozen) or project root (dev)
_data_env = os.environ.get("TGB_DATA_DIR")
if _data_env:
    _data_root = Path(_data_env)
elif getattr(sys, "frozen", False):
    _data_root = Path(sys.executable).parent / "tgb_data"
else:
    _data_root = Path(__file__).resolve().parent.parent / "data"
_data_root.mkdir(parents=True, exist_ok=True)

SECRET_KEY = "jh-local-dev-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.sites",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crm.apps.CrmConfig",
    "chat.apps.ChatConfig",
    "linkedin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "linkedin.tgb_urls"

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_data_root / "db.sqlite3"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
STATIC_URL = "/static/"
STATIC_ROOT = _data_root / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = _data_root / "media"
LOGIN_URL = "/admin/login/"
DEFAULT_FROM_EMAIL = "noreply@localhost"
EMAIL_SUBJECT_PREFIX = "JH: "
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
TESTING = sys.argv[1:2] == ["test"]
