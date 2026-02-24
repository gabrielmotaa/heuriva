"""
Production settings for Heuriva.
Enable with: ENVIRONMENT=production
"""

from heuriva.settings.base import *  # noqa: F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Language Settings
LANGUAGE_CODE = "pt-br"

# Security Settings
# https://docs.djangoproject.com/en/5.2/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405

# HSTS (HTTP Strict Transport Security)
# https://docs.djangoproject.com/en/5.2/ref/middleware/#http-strict-transport-security
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)  # noqa: F405 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(  # noqa: F405
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)  # noqa: F405

# Cookie Security
# https://docs.djangoproject.com/en/5.2/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)  # noqa: F405
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)  # noqa: F405

# Additional security headers
# https://docs.djangoproject.com/en/5.2/ref/settings/#secure-content-type-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Proxy headers (for reverse proxy setups like Nginx, Caddy, Traefik)
# https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF Trusted Origins
# Add your domain here
# https://docs.djangoproject.com/en/5.2/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = config(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    cast=Csv(),  # noqa: F405
)

# WhiteNoise configuration for static files
# https://whitenoise.readthedocs.io/en/latest/django.html
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# S3-compatible storage (Cloudflare R2, AWS S3, etc.)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")  # noqa: F405
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL")  # noqa: F405
AWS_S3_ACCESS_KEY_ID = config("AWS_S3_ACCESS_KEY_ID")  # noqa: F405
AWS_S3_SECRET_ACCESS_KEY = config("AWS_S3_SECRET_ACCESS_KEY")  # noqa: F405
AWS_S3_SIGNATURE_VERSION = "s3v4"

# Email configuration (configure for production)
# https://docs.djangoproject.com/en/5.2/topics/email/
EMAIL_BACKEND = config(  # noqa: F405
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)  # noqa: F405
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)  # noqa: F405
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@heuriva.com.br")  # noqa: F405
SERVER_EMAIL = config("SERVER_EMAIL", default="errors@heuriva.com.br")  # noqa: F405

# Logging configuration
# https://docs.djangoproject.com/en/5.2/topics/logging/
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "heuriva": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

# Admin email for error reports
ADMINS = [
    ("Gabriel Mota", config("ADMIN_EMAIL")),  # noqa: F405
]

MANAGERS = ADMINS
