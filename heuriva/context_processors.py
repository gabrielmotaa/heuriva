"""Context processors for making variables available in all templates."""

from django.conf import settings


def feature_flags(request):
    """Make feature flags available in all templates."""
    return {
        "REGISTRATION_ENABLED": settings.REGISTRATION_ENABLED,
        "CRAWLER_USER_AGENT": settings.CRAWLER_USER_AGENT,
    }
