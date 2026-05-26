from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models.functions import Length
from django.shortcuts import get_object_or_404, redirect, render

from heuriva.apps.heuristics.models import HeuristicGroup

from .forms import AnalysisCreateForm
from .models import Analysis, Project
from .tasks import run_crawler


def project_list(request):
    """List all projects for the current user."""
    projects = (
        Project.objects.filter(user=request.user)
        .prefetch_related(
            "analyses__pages"  # Prefetch pages without html_content
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "analysis/project_list.html",
        {
            "projects": projects,
        },
    )


def project_detail(request, short_id):
    """Show details of a specific project."""
    project = get_object_or_404(
        Project.objects.prefetch_related(
            "analyses__pages"  # Prefetch pages for metrics calculation
        ),
        short_id=short_id,
        user=request.user,
    )

    # Paginate analyses
    analyses_list = project.analyses.all()
    paginator = Paginator(analyses_list, 10)  # 10 analyses per page
    page_number = request.GET.get("page")
    analyses_page = paginator.get_page(page_number)

    # Get the last completed analysis to show the current valid score
    last_completed_analysis = project.analyses.filter(
        status=Analysis.Status.COMPLETED
    ).first()

    return render(
        request,
        "analysis/project_detail.html",
        {
            "project": project,
            "analyses_page": analyses_page,
            "last_completed_analysis": last_completed_analysis,
        },
    )


def project_create(request):
    """Create a new project."""

    if request.method == "POST":
        name = request.POST.get("name")
        url = request.POST.get("url")
        screenshot = request.FILES.get("homepage_screenshot")

        if name and url:
            project = Project.objects.create(name=name, url=url, user=request.user)

            if screenshot:
                project.homepage_screenshot.save(screenshot.name, screenshot, save=True)

            messages.success(request, "Projeto criado com sucesso!")
            return redirect("analysis:project_detail", short_id=project.short_id)
        else:
            messages.error(request, "Nome e URL são obrigatórios.")

    return render(request, "analysis/project_create.html")


def project_update(request, short_id):
    """Update an existing project."""
    project = get_object_or_404(Project, short_id=short_id, user=request.user)

    if request.method == "POST":
        # Check if it's a delete action
        if request.POST.get("action") == "delete":
            project_name = project.name
            project.delete()
            messages.success(request, f'Projeto "{project_name}" excluído com sucesso.')
            return redirect("analysis:project_list")

        # Otherwise, it's an update
        name = request.POST.get("name")
        url = request.POST.get("url")
        screenshot = request.FILES.get("homepage_screenshot")

        if name and url:
            project.name = name
            project.url = url

            # Only update screenshot if a new one is uploaded
            if screenshot:
                project.homepage_screenshot = screenshot

            project.save()
            messages.success(request, "Projeto atualizado com sucesso!")
            return redirect("analysis:project_list")
        else:
            messages.error(request, "Nome e URL são obrigatórios.")

    return render(
        request,
        "analysis/project_update.html",
        {
            "project": project,
        },
    )


def analysis_create(request, project_short_id):
    """Create a new analysis for a project."""
    project = get_object_or_404(Project, short_id=project_short_id, user=request.user)

    if request.method == "POST":
        form = AnalysisCreateForm(request.POST)

        if form.is_valid():
            # Create the analysis first
            analysis = Analysis.objects.create(
                project=project,
                score="",  # Will be calculated after analysis finishes
                heuristics_group=form.cleaned_data["heuristics_group"],
                status=Analysis.Status.PENDING,
            )

            # Get the crawler configuration with analysis_id
            crawler_config = form.get_crawler_config(project.url)
            crawler_config["analysis_id"] = analysis.id

            # Trigger the crawler task asynchronously
            try:
                task = run_crawler.delay(**crawler_config)

                # Update analysis with task information
                analysis.celery_task_id = task.id
                analysis.status = Analysis.Status.CRAWLING
                analysis.save(update_fields=["celery_task_id", "status"])

                messages.success(
                    request,
                    f"Análise #{analysis.sequence_number} criada com sucesso! "
                    f"O crawler está coletando os dados em background.",
                )
            except Exception as e:
                # Update analysis status to failed
                analysis.status = Analysis.Status.FAILED
                analysis.error_message = str(e)
                analysis.save(update_fields=["status", "error_message"])

                messages.error(
                    request,
                    "Não foi possível iniciar a coleta de dados. "
                    "Por favor, tente novamente mais tarde ou entre em contato com o suporte.",
                )

            return redirect("analysis:project_detail", short_id=project.short_id)
    else:
        form = AnalysisCreateForm()

    heuristic_groups = HeuristicGroup.objects.all()

    return render(
        request,
        "analysis/analysis_create.html",
        {
            "project": project,
            "heuristic_groups": heuristic_groups,
            "form": form,
        },
    )


def analysis_detail(request, short_id):
    """Show details of a specific analysis."""
    analysis = get_object_or_404(
        Analysis.objects.prefetch_related(
            "pages__heuristic_evaluations__heuristic"  # Prefetch related data
        ),
        short_id=short_id,
        project__user=request.user,
    )

    # Get pages ordered by path length (shortest first)
    pages = analysis.pages.annotate(path_length=Length("path")).order_by("path_length")

    return render(
        request,
        "analysis/analysis_detail.html",
        {
            "analysis": analysis,
            "pages": pages,
        },
    )
