# config/settings.py
"""
Settings for the FlipWhizz Growth Hub.

Everything environment-specific comes from environment variables (or a .env
file in development). See .env.example for the full list.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --- Core -------------------------------------------------------------------

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

if not DEBUG and SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Set DJANGO_SECRET_KEY in production.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "core",
    "moments",
    "printables",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------------
# MySQL in production and CI. DB_ENGINE=sqlite is allowed for quick local runs.

DB_ENGINE = os.environ.get("DB_ENGINE", "mysql")

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    import pymysql

    pymysql.install_as_MySQLdb()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "growthhub"),
            "USER": os.environ.get("DB_USER", "growthhub"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

    # Hosted MySQL (e.g. Aiven) requires TLS. DB_SSL_CA holds the provider's CA
    # certificate as PEM text, which is easy to paste into an environment
    # variable. It's written to a temp file because the driver needs a path.
    _ssl_ca = os.environ.get("DB_SSL_CA", "").strip()
    if _ssl_ca:
        import tempfile

        _ca_path = Path(tempfile.gettempdir()) / "db-ca.pem"
        if not _ca_path.exists() or _ca_path.read_text() != _ssl_ca + "\n":
            _ca_path.write_text(_ssl_ca + "\n")
        DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": str(_ca_path)}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n -------------------------------------------------------------------

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# --- Static and public URLs -------------------------------------------------
# Phase 1: served at the root of stories.flipwhizz.com (defaults below).
# Phase 2: mounted at /stories (WSGIScriptAlias /stories) and proxied from
# flipwhizz.com/stories/*. Then set STATIC_URL=/stories/static/ and
# PUBLIC_BASE_URL=https://flipwhizz.com so canonical tags, the sitemap and API
# links point at flipwhizz.com, not the origin server. See DEPLOY.md.

STATIC_URL = os.environ.get("STATIC_URL", "/static/")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# --- Security (production) --------------------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))

# --- Logging ----------------------------------------------------------------
# Logs never include child names or story text. See printables/services.py.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

# --- App settings -----------------------------------------------------------

SITE_NAME = "FlipWhizz Stories"
FLIPWHIZZ_URL = os.environ.get("FLIPWHIZZ_URL", "https://flipwhizz.com")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "FlipWhizz <hello@flipwhizz.com>")

# Abuse and cost limits for the free printable.
PRINTABLE_LIMIT_PER_EMAIL_PER_DAY = int(os.environ.get("PRINTABLE_LIMIT_PER_EMAIL_PER_DAY", "3"))
PRINTABLE_LIMIT_PER_IP_PER_DAY = int(os.environ.get("PRINTABLE_LIMIT_PER_IP_PER_DAY", "5"))
PRINTABLE_GLOBAL_LIMIT_PER_DAY = int(os.environ.get("PRINTABLE_GLOBAL_LIMIT_PER_DAY", "200"))
PRINTABLE_MAX_ATTEMPTS = int(os.environ.get("PRINTABLE_MAX_ATTEMPTS", "3"))

# Where printables get made:
#   False (server with cron): the form queues the request and cron sends it.
#   True (Vercel): the form makes and sends it straight away; anything that
#   fails is retried by the scheduled call to /internal/cron/.
PRINTABLE_PROCESS_INLINE = env_bool("PRINTABLE_PROCESS_INLINE", False)

# Shared secret for /internal/cron/. Unset means the URL returns 404.
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# Personal data retention (UK Children's Code: keep the minimum, for the minimum time).
PRINTABLE_RETENTION_DAYS = int(os.environ.get("PRINTABLE_RETENTION_DAYS", "30"))

# Salt for hashing IP addresses. IPs are never stored in plain text.
IP_HASH_SALT = os.environ.get("IP_HASH_SALT", SECRET_KEY)
