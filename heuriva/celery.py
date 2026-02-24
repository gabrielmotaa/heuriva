import os

from celery import Celery

environment = os.getenv("ENVIRONMENT", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"heuriva.settings.{environment}")
app = Celery("heuriva")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
