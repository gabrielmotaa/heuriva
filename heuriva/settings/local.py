from heuriva.settings.base import *  # noqa: F403

DEBUG = True

SECRET_KEY = "insecure-secret-key"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Add development-only apps
INSTALLED_APPS += [  # noqa: F405
    "django_browser_reload",
    "django_watchfiles",
]

# Add development-only middleware
MIDDLEWARE.insert(0, "django_browser_reload.middleware.BrowserReloadMiddleware")  # noqa: F405

# Disable security features in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
