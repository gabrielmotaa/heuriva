from django.db import models
from django.utils.translation import gettext_lazy as _


class Heuristic(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name=_("name"))
    description = models.TextField(verbose_name=_("description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("heuristic")
        verbose_name_plural = _("heuristics")

    def __str__(self):
        return self.name


class HeuristicGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(verbose_name=_("name"))
    heuristics = models.ManyToManyField(
        "Heuristic", related_name="groups", verbose_name=_("heuristics")
    )
    description = models.TextField(verbose_name=_("description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("heuristic group")
        verbose_name_plural = _("heuristic groups")

    def __str__(self):
        return self.name


class HeuristicEvaluation(models.Model):
    class Level(models.TextChoices):
        EXCELLENT = "excellent", _("Excellent")
        GOOD = "good", _("Good")
        FAIR = "fair", _("Fair")
        POOR = "poor", _("Poor")
        CRITICAL = "critical", _("Critical")

    id = models.AutoField(primary_key=True)
    page = models.ForeignKey(
        "analysis.Page",
        on_delete=models.CASCADE,
        related_name="heuristic_evaluations",
        verbose_name=_("page"),
    )
    heuristic = models.ForeignKey(
        "Heuristic",
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name=_("heuristic"),
    )
    level = models.CharField(choices=Level, verbose_name=_("level"))
    problems = models.TextField(blank=True, verbose_name=_("problems"))
    recommendations = models.TextField(blank=True, verbose_name=_("recommendations"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("heuristic evaluation")
        verbose_name_plural = _("heuristic evaluations")
        unique_together = [["page", "heuristic"]]
