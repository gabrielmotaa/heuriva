import io
import zipfile

from django.contrib import admin
from django.db import connection
from django.http import HttpResponse
from django.utils.html import escape, format_html
from django.utils.translation import gettext_lazy as _

from .models import Analysis, Page, Project


class AnalysisInline(admin.TabularInline):
    model = Analysis
    extra = 0
    fields = ("score", "heuristics_group", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    fields = ("path", "screenshot", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True

    def get_queryset(self, request):
        """Override to exclude html_content from inline display."""
        return super().get_queryset(request).defer("html_content")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "user", "get_analyses_count", "created_at")
    list_filter = ("created_at", "updated_at", "user")
    search_fields = ("name", "url", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "display_homepage_screenshot")
    inlines = [AnalysisInline]
    fieldsets = (
        (_("Project Information"), {"fields": ("name", "url", "user")}),
        (
            _("Screenshot"),
            {"fields": ("homepage_screenshot", "display_homepage_screenshot")},
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Analyses"))
    def get_analyses_count(self, obj):
        return obj.analyses.count()

    @admin.display(description=_("Preview"))
    def display_homepage_screenshot(self, obj):
        if obj.homepage_screenshot:
            return format_html(
                """<img src="{}" style="max-width: 300px; max-height: 300px;" />""",
                obj.homepage_screenshot.url,
            )
        return _("No screenshot")


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_project_name",
        "status",
        "score",
        "heuristics_group",
        "get_pages_count",
        "created_at",
    )
    list_filter = ("status", "score", "heuristics_group", "created_at", "updated_at")
    search_fields = ("project__name", "project__url", "score", "celery_task_id")
    readonly_fields = (
        "status",
        "celery_task_id",
        "error_message",
        "created_at",
        "updated_at",
    )
    inlines = [PageInline]
    fieldsets = (
        (
            _("Analysis"),
            {"fields": ("project", "score", "heuristics_group")},
        ),
        (
            _("Status"),
            {
                "fields": ("status", "celery_task_id", "error_message"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Project"))
    def get_project_name(self, obj):
        return obj.project.name

    @admin.display(description=_("Pages"))
    def get_pages_count(self, obj):
        return obj.get_total_pages()


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("path", "get_project_name", "get_project_url", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("path", "analysis__project__name")
    actions = ["export_html_content"]
    readonly_fields = (
        "created_at",
        "updated_at",
        "display_screenshot",
        "display_html_preview",
        "display_html_stats",
    )
    fieldsets = (
        (_("Page Information"), {"fields": ("analysis", "path")}),
        (_("Screenshot"), {"fields": ("screenshot", "display_screenshot")}),
        (
            _("HTML Content"),
            {
                "fields": ("display_html_stats", "display_html_preview"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Dates"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        """Override to defer html_content by default in list view."""
        qs = super().get_queryset(request)
        return qs.defer("html_content").select_related("analysis__project")

    def get_object(self, request, object_id, from_field=None):
        """
        When viewing/editing a single page, include html_content.
        """
        queryset = self.get_queryset(request)
        model = queryset.model
        field = (
            model._meta.pk if from_field is None else model._meta.get_field(from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return (
                Page.objects.with_html_content()
                .select_related("analysis__project")
                .get(pk=object_id)
            )
        except (model.DoesNotExist, ValueError):
            return None

    @admin.display(description=_("Project URL"))
    def get_project_url(self, obj):
        return obj.analysis.project.url

    @admin.display(description=_("Project"))
    def get_project_name(self, obj):
        return obj.analysis.project.name

    @admin.display(description=_("Preview"))
    def display_screenshot(self, obj):
        if obj.screenshot:
            return format_html(
                """<img src="{}" style="max-width: 600px; max-height: 400px;" />""",
                obj.screenshot.url,
            )
        return _("No screenshot")

    @admin.display(description=_("HTML Statistics"))
    def display_html_stats(self, obj):
        """Display statistics about the HTML content."""
        # Get compressed size directly from database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT octet_length(html_content) FROM analysis_page WHERE id = %s",
                [obj.id],
            )
            result = cursor.fetchone()
            compressed_size = result[0] if result and result[0] else 0

        if compressed_size == 0:
            return format_html(
                """
                <div style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
                    <strong>⚠️ No HTML content stored</strong>
                </div>
                """
            )

        # Load html_content if deferred
        try:
            html_content = obj.html_content
        except AttributeError:
            obj = Page.objects.with_html_content().get(pk=obj.pk)
            html_content = obj.html_content

        decompressed_size = len(html_content.encode("utf-8")) if html_content else 0

        if decompressed_size == 0:
            return format_html(
                """
                <div style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
                    <strong>⚠️ HTML content is empty</strong>
                </div>
                """
            )

        compression_ratio = (1 - compressed_size / decompressed_size) * 100
        compression_factor = decompressed_size / compressed_size
        saved_bytes = decompressed_size - compressed_size

        # Format values before passing to format_html
        decompressed_kb = decompressed_size / 1024
        compressed_kb = compressed_size / 1024
        saved_kb = saved_bytes / 1024

        return format_html(
            """
            <div style="padding: 15px; background-color: #e7f3ff; border: 1px solid #2196F3; border-radius: 4px;">
                <strong>📊 HTML Compression Statistics</strong><br><br>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px;"><strong>Original Size:</strong></td>
                        <td>{} bytes ({} KB)</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px;"><strong>Compressed Size:</strong></td>
                        <td>{} bytes ({} KB)</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border-top: 1px solid #ddd; padding-top: 10px;">
                            <strong>Compression Ratio:</strong>
                        </td>
                        <td style="border-top: 1px solid #ddd; padding-top: 10px;">
                            <span style="color: #4CAF50; font-weight: bold;">{}%</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 5px;"><strong>Compression Factor:</strong></td>
                        <td><span style="color: #2196F3; font-weight: bold;">{}x</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 5px;"><strong>Space Saved:</strong></td>
                        <td><span style="color: #FF9800; font-weight: bold;">{} bytes ({} KB)</span></td>
                    </tr>
                </table>
            </div>
            """,
            f"{decompressed_size:,}",
            f"{decompressed_kb:.2f}",
            f"{compressed_size:,}",
            f"{compressed_kb:.2f}",
            f"{compression_ratio:.1f}",
            f"{compression_factor:.2f}",
            f"{saved_bytes:,}",
            f"{saved_kb:.2f}",
        )

    @admin.display(description=_("HTML Preview"))
    def display_html_preview(self, obj):
        """Display a collapsible preview of the HTML content."""
        # Check if html_content is loaded
        try:
            html_content = obj.html_content
        except AttributeError:
            # Field is deferred, need to load it
            obj = Page.objects.with_html_content().get(pk=obj.pk)
            html_content = obj.html_content

        if not html_content:
            return format_html(
                """
                <div style="padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">
                    <strong>❌ No HTML content available</strong>
                </div>
                """
            )

        preview_length = 1000
        is_truncated = len(html_content) > preview_length
        preview = html_content[:preview_length] if is_truncated else html_content

        return format_html(
            """
            <div>
                <div style="
                    padding: 15px; 
                    background-color: #f5f5f5; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                    font-family: monospace; 
                    font-size: 12px; 
                    white-space: pre-wrap; 
                    word-wrap: break-word; 
                    max-height: 400px; 
                    overflow-y: auto;
                ">{}{}</div>
                <div style="margin-top: 10px; padding: 10px; background-color: #e3f2fd; border-radius: 4px;">
                    <strong>💡 Tip:</strong> This is the raw HTML source code. 
                    Use the export action to download the full file.
                </div>
            </div>
            """,
            escape(preview),
            '<br><br><strong style="color: #ff9800;">... (truncated)</strong>'
            if is_truncated
            else "",
        )

    @admin.action(description=_("Export HTML content of selected pages"))
    def export_html_content(self, request, queryset):
        """Export HTML content of selected pages as a ZIP file."""
        # Load html_content for selected pages
        pages = queryset.model.objects.with_html_content().filter(
            pk__in=queryset.values_list("pk", flat=True)
        )

        if not pages.exists():
            self.message_user(request, _("No pages selected."), level="warning")
            return

        # Filter pages that actually have HTML content
        pages_with_content = [page for page in pages if page.html_content]

        if not pages_with_content:
            self.message_user(
                request,
                _("None of the selected pages have HTML content to export."),
                level="warning",
            )
            return

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for page in pages_with_content:
                # Create safe filename
                filename = f"{page.analysis.project.name}_{page.path}".replace(
                    "/", "_"
                ).replace(" ", "_")
                if filename.startswith("_"):
                    filename = filename[1:]
                if not filename:
                    filename = "index"
                filename = f"{filename}.html"

                # Add file to ZIP
                zip_file.writestr(filename, page.html_content)

        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=pages_html_export.zip"

        self.message_user(
            request,
            _("Successfully exported HTML content from {} page(s).").format(
                len(pages_with_content)
            ),
        )
        return response
