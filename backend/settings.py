# backend/settings.py
from pathlib import Path
import os
import base64

import dj_database_url
from django.core.management.utils import get_random_secret_key
from cryptography.hazmat.primitives import serialization

BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================================
# ✅ .env SOLO LOCAL (Render usa Environment Variables)
# ==========================================================
if os.environ.get("RENDER") != "true":
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except Exception:
        pass

# =========================
# BASICO
# =========================
SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-" + get_random_secret_key())

DEBUG = os.environ.get("DEBUG", "False").strip().lower() == "true"

RENDER = (os.environ.get("RENDER") or "").strip().lower() == "true"
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

# =========================
# PUSH / VAPID
# =========================
VAPID_PUBLIC_KEY_FALLBACK = (
    "BG1zLGX1ICKlfEjvz48a-4n2uhtiaUT54GP62cJALk6p0u35Zyyll7ghaXQBduO7BKpjXYLXwMWzL7PAKA0UnP0"
)

def _strip_bytes_wrapper(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    if (v.startswith("b'") and v.endswith("'")) or (v.startswith('b"') and v.endswith('"')):
        v = v[2:-1]
    return v

def _env_multiline(name: str, default: str = "") -> str:
    raw = os.environ.get(name, default)
    raw = _strip_bytes_wrapper(raw)
    if "\\n" in raw:
        raw = raw.replace("\\n", "\n")
    return raw.strip()

def _clean_base64url(value: str) -> str:
    return (value or "").replace("\n", "").replace("\r", "").replace(" ", "").strip()

VAPID_PUBLIC_PEM = _env_multiline("VAPID_PUBLIC_PEM", "")
VAPID_PRIVATE_PEM = _env_multiline("VAPID_PRIVATE_PEM", "")

VAPID_PUBLIC_KEY = _clean_base64url(os.environ.get("VAPID_PUBLIC_KEY", ""))
VAPID_PRIVATE_KEY = _clean_base64url(os.environ.get("VAPID_PRIVATE_KEY", ""))

VAPID_SUBJECT = (os.environ.get("VAPID_SUBJECT", "mailto:admin@piscinas-app.local") or "").strip()

if not VAPID_PUBLIC_KEY:
    if VAPID_PUBLIC_PEM:
        try:
            pub = serialization.load_pem_public_key(VAPID_PUBLIC_PEM.encode("utf-8"))
            nums = pub.public_numbers()
            x = nums.x.to_bytes(32, "big")
            y = nums.y.to_bytes(32, "big")
            uncompressed = b"\x04" + x + y
            VAPID_PUBLIC_KEY = base64.urlsafe_b64encode(uncompressed).decode("utf-8").rstrip("=")
        except Exception:
            VAPID_PUBLIC_KEY = VAPID_PUBLIC_KEY_FALLBACK
    else:
        VAPID_PUBLIC_KEY = VAPID_PUBLIC_KEY_FALLBACK

VAPID_PRIVATE_KEY = VAPID_PRIVATE_PEM

# =========================
# HOSTS
# =========================
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "piscinas-app.onrender.com",
    "piscinas-app-1.onrender.com",
    ".onrender.com",
]
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

ENV_ALLOWED = os.environ.get("ALLOWED_HOSTS", "").strip()
if ENV_ALLOWED:
    ALLOWED_HOSTS += [h.strip() for h in ENV_ALLOWED.split(",") if h.strip()]

ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))

# =========================
# ✅ PROXY / HTTPS (Render)
# =========================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SESSION_COOKIE_SECURE = True if RENDER else (not DEBUG)
CSRF_COOKIE_SECURE = True if RENDER else (not DEBUG)

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# =========================
# CSRF para Render
# =========================
CSRF_TRUSTED_ORIGINS = [
    "https://piscinas-app.onrender.com",
    "https://piscinas-app-1.onrender.com",
]
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")
CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")

# =========================
# APPS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "clientes",
    "contratos",
    "trabajadores",
    "mantenimientos",
    "checklists",
    "inventario",
    "finanzas",

    "dashboard.apps.DashboardConfig",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"
WSGI_APPLICATION = "backend.wsgi.application"

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
                "dashboard.context_processors.vapid_public_key",
            ],
        },
    },
]

# =========================
# DATABASE
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =========================
# PASSWORDS
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# LOCALIZACION
# =========================
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC / MEDIA
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

if (BASE_DIR / "static").exists():
    STATICFILES_DIRS = [BASE_DIR / "static"]

if DEBUG:
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_MAX_AGE = 0
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# LOGIN
# =========================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/inicio/"
LOGOUT_REDIRECT_URL = "/login/"

# =========================
# SEGURIDAD PRODUCCION
# =========================
SECURE_SSL_REDIRECT = False

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

# =========================
# LOGGING
# =========================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": True},
    },
}