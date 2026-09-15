import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _bool_env(key: str, default: bool = False) -> bool:
    return os.environ.get(key, "true" if default else "false").lower() in ("true", "1", "yes")


def _csv_env(key: str, default: list[str]) -> list[str]:
    raw = os.environ.get(key, "")
    if not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
DEBUG = _bool_env("DEBUG", default=False)

ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "screening",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "resume_screener"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS: allow specific origins via env, or '*' when CORS_ALLOW_ALL=true
CORS_ALLOW_ALL_ORIGINS = _bool_env("CORS_ALLOW_ALL", default=DEBUG)
CORS_ALLOWED_ORIGINS = _csv_env("CORS_ALLOWED_ORIGINS", [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
])

# In dev, allow any localhost port (Next.js may use 3001+ if 3000 is taken)
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
    ]

FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Resume Screening Tool API",
    "DESCRIPTION": (
        "Upload a candidate's resume (PDF) and a job description. The service extracts text, "
        "embeds it with Ollama, scores the match against the role, and lets you ask RAG questions "
        "about the candidate. Analysis runs asynchronously - poll the record endpoint until the "
        "status is 'completed'."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "COMPONENT_SPLIT_REQUEST": True,
}

USE_OLLAMA = os.environ.get("USE_OLLAMA", "true")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
# NOTE: the embedding model's output dimension MUST match ResumeChunk.embedding
# (VectorField) in screening/models.py (currently 1024 -> mxbai-embed-large).
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.2")