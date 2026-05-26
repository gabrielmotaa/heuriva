from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

# Feature flags
REGISTRATION_ENABLED = config("REGISTRATION_ENABLED", default=True, cast=bool)

INSTALLED_APPS = [
    # Project
    "heuriva.apps.accounts",
    "heuriva.apps.pages",
    "heuriva.apps.analysis",
    "heuriva.apps.heuristics",
    # Third party
    "django_celery_results",
    "anymail",
    # Contrib
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "heuriva.urls"

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
                "heuriva.context_processors.feature_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "heuriva.wsgi.application"


DATABASES = {
    "default": dj_database_url.parse(
        url=config("DATABASE_URL", "sqlite:///" + str(BASE_DIR / "db.sqlite3")),  # type: ignore[arg-type]
        conn_max_age=600,  # 10 minutes
        conn_health_checks=True,
    ),
}

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

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR.parent / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR.parent / "media"  # /app/media for shared volume

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

TEST_RUNNER = "django_rich.test.RichRunner"

LOGIN_REDIRECT_URL = "analysis:project_list"
LOGOUT_REDIRECT_URL = "pages:index"

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="django-db")

# Route the crawler task to its own queue so a dedicated worker with
# concurrency=1 ensures only one Playwright instance runs at a time.
CELERY_TASK_ROUTES = {
    "heuriva.apps.analysis.tasks.run_crawler": {"queue": "crawler"},
}


# Zstandard compression level (1-22, where 5 is default)
# Higher = better compression but slower, Lower = faster but less compression
ZSTD_COMPRESSION_LEVEL = config("ZSTD_COMPRESSION_LEVEL", default=5, cast=int)

# LLM Configuration
LLM_PROVIDER = config(
    "LLM_PROVIDER", default="gemini"
)  # gemini, openai, anthropic, etc.
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")  # Required if using Gemini
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.5-flash")

# LLM Rate Limiting Configuration
# Maximum number of LLM API calls per minute
LLM_MAX_CALLS_PER_MINUTE = config("LLM_MAX_CALLS_PER_MINUTE", default=15, cast=int)
# Delay in seconds between consecutive LLM calls (alternative to calls per minute)
LLM_MIN_DELAY_BETWEEN_CALLS = config(
    "LLM_MIN_DELAY_BETWEEN_CALLS", default=0, cast=float
)

# Crawler Configuration
CRAWLER_USER_AGENT = config("CRAWLER_USER_AGENT", default="HeurivaCrawler/1.0")
