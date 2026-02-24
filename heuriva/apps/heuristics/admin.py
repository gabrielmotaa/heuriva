from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Heuristic, HeuristicEvaluation, HeuristicGroup


class HeuristicInline(admin.TabularInline):
    model = HeuristicGroup.heuristics.through
    extra = 1
    verbose_name = _("Heuristic")
    verbose_name_plural = _("Heuristics")


@admin.register(Heuristic)
class HeuristicAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (_("General Information"), {"fields": ("name", "description")}),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(HeuristicGroup)
class HeuristicGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "get_heuristics_count", "created_at", "updated_at")
    search_fields = ("name", "description")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("heuristics",)
    fieldsets = (
        (_("General Information"), {"fields": ("name", "description")}),
        (_("Heuristics"), {"fields": ("heuristics",)}),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Heuristics Count"))
    def get_heuristics_count(self, obj):
        return obj.heuristics.count()


@admin.register(HeuristicEvaluation)
class HeuristicEvaluationAdmin(admin.ModelAdmin):
    list_display = ("get_page_path", "heuristic", "level", "created_at")
    list_filter = ("level", "heuristic", "created_at")
    search_fields = ("page__path", "heuristic__name", "problems", "recommendations")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (_("Evaluation"), {"fields": ("page", "heuristic", "level")}),
        (_("Details"), {"fields": ("problems", "recommendations")}),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Page"))
    def get_page_path(self, obj):
        return obj.page.path
