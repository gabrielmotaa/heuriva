import secrets
import uuid

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .fields import ZstdCompressedTextField


def generate_short_id():
    """Generate a URL-safe short ID (~8 chars, 2.8x10^14 combinations)."""
    return secrets.token_urlsafe(6)


def upload_to_media(instance, filename):
    """
    Generate a unique filename with UUID4 for all media files.
    All files are stored in the root media directory.
    """
    # Get file extension
    ext = filename.split(".")[-1] if "." in filename else ""
    # Generate UUID4 filename
    new_filename = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
    return new_filename


class PageManager(models.Manager):
    """
    Custom manager for Page model that defers html_content by default.
    Use .with_html_content() to include it when needed.
    """

    def get_queryset(self):
        return super().get_queryset().defer("html_content")

    def with_html_content(self):
        """Include html_content in the query."""
        # Use all_fields=True to get a fresh queryset without defers
        return super().get_queryset()


class Project(models.Model):
    id = models.AutoField(primary_key=True)
    short_id = models.CharField(
        max_length=12,
        unique=True,
        default=generate_short_id,
        editable=False,
        verbose_name=_("short ID"),
    )
    name = models.CharField(verbose_name=_("name"))
    url = models.URLField(verbose_name=_("URL"))
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name=_("user"),
    )
    homepage_screenshot = models.ImageField(
        upload_to=upload_to_media,
        blank=True,
        null=True,
        verbose_name=_("homepage screenshot"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("project")
        verbose_name_plural = _("projects")

    def __str__(self):
        return self.name

    def set_homepage_screenshot_from_analysis(self, analysis: "Analysis") -> None:
        home_page = analysis.get_home_page()
        if home_page and home_page.screenshot:
            self.homepage_screenshot = home_page.screenshot


class Analysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CRAWLING = "crawling", _("Crawling")
        CRAWL_COMPLETED = "crawl_completed", _("Crawl Completed")
        ANALYZING = "analyzing", _("Analyzing Heuristics")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    id = models.AutoField(primary_key=True)
    short_id = models.CharField(
        max_length=12,
        unique=True,
        default=generate_short_id,
        editable=False,
        verbose_name=_("short ID"),
    )
    sequence_number = models.PositiveIntegerField(
        editable=False,
        verbose_name=_("sequence number"),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="analyses",
        verbose_name=_("project"),
    )
    score = models.CharField(verbose_name=_("score"))
    heuristics_group = models.ForeignKey(
        "heuristics.HeuristicGroup",
        on_delete=models.CASCADE,
        related_name="analyses",
        verbose_name=_("heuristics group"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("status"),
    )
    celery_task_id = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("celery task id")
    )
    error_message = models.TextField(
        blank=True, null=True, verbose_name=_("error message")
    )
    executive_summary = models.TextField(
        blank=True, null=True, verbose_name=_("executive summary")
    )
    priorities = models.JSONField(blank=True, null=True, verbose_name=_("priorities"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("analysis")
        verbose_name_plural = _("analyses")
        ordering = ["-created_at"]  # Most recent first

    def save(self, *args, **kwargs):
        if self.sequence_number is None and self.project_id:
            with transaction.atomic():
                # Lock project rows to prevent race conditions
                last = (
                    Analysis.objects.select_for_update()
                    .filter(project_id=self.project_id)
                    .aggregate(max_seq=models.Max("sequence_number"))["max_seq"]
                    or 0
                )
                self.sequence_number = last + 1
                super().save(*args, **kwargs)
                return
        super().save(*args, **kwargs)

    def get_total_pages(self):
        return self.pages.count()

    def get_evaluated_pages(self):
        return self.pages.filter(heuristic_evaluations__isnull=False).distinct()

    def get_evaluated_pages_count(self):
        return self.get_evaluated_pages().count()

    def get_home_page(self) -> "Page | None":
        return self.pages.filter(path="/").first()


class Page(models.Model):
    id = models.AutoField(primary_key=True)
    analysis = models.ForeignKey(
        Analysis,
        on_delete=models.CASCADE,
        related_name="pages",
        verbose_name=_("analysis"),
    )
    path = models.CharField(verbose_name=_("path"))
    screenshot = models.ImageField(
        upload_to=upload_to_media,
        blank=True,
        null=True,
        verbose_name=_("screenshot"),
    )
    html_content = ZstdCompressedTextField(
        blank=True, null=True, verbose_name=_("HTML content")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    objects = PageManager()

    class Meta:
        verbose_name = _("page")
        verbose_name_plural = _("pages")

    def __str__(self):
        return self.path
