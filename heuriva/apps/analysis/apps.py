from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "heuriva.apps.analysis"
    verbose_name = _("Analysis")
