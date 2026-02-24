from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HeuristicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "heuriva.apps.heuristics"
    verbose_name = _("Heuristics")
