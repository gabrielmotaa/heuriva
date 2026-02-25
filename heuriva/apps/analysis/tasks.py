import hashlib
import logging

from celery import shared_task
from django.conf import settings

from heuriva.apps.analysis.crawler import PlaywrightCrawler
from heuriva.apps.analysis.models import Analysis, Page
from heuriva.apps.heuristics.models import HeuristicEvaluation
from heuriva.llm import get_llm_provider

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_heuristic_analysis(self, analysis_id: int):
    """
    Run heuristic analysis on all pages of an analysis using LLM.

    Args:
        analysis_id: ID of the Analysis to evaluate
    """
    try:
        # Get the analysis
        analysis = (
            Analysis.objects.select_related("heuristics_group")
            .prefetch_related("heuristics_group__heuristics")
            .get(id=analysis_id)
        )

        # Update status to analyzing
        analysis.status = Analysis.Status.ANALYZING
        analysis.save(update_fields=["status"])

        # Get heuristics from the group
        heuristics = [
            {
                "id": h.id,
                "name": h.name,
                "description": h.description,
            }
            for h in analysis.heuristics_group.heuristics.all()
        ]

        if not heuristics:
            raise ValueError(
                f"No heuristics found in group {analysis.heuristics_group.id}"
            )

        # Initialize LLM provider using factory
        llm_provider = get_llm_provider()

        # Get all pages with HTML content
        pages = Page.objects.with_html_content().filter(analysis=analysis)

        # Find previous completed analysis with same heuristics group for this project
        # This enables consistency: if analyzing the same page again with unchanged HTML,
        # the LLM will maintain the same score instead of producing slightly different results
        previous_analysis = (
            Analysis.objects.filter(
                project=analysis.project,
                heuristics_group=analysis.heuristics_group,
                status=Analysis.Status.COMPLETED,
            )
            .exclude(id=analysis.id)
            .order_by("-created_at")
            .first()
        )

        total_score = 0.0
        pages_analyzed = 0
        all_results = []  # Store all analysis results

        for page in pages:
            if not page.html_content:
                continue

            # Try to find corresponding page from previous analysis
            previous_score = None
            previous_evaluations = None
            html_changed = True  # Assume HTML changed unless proven otherwise

            if previous_analysis:
                previous_page = (
                    Page.objects.filter(analysis=previous_analysis, path=page.path)
                    .prefetch_related("heuristic_evaluations__heuristic")
                    .first()
                )

                if previous_page:
                    # Compare HTML content to detect if page changed
                    # Handle both bytes and string content, and None values
                    if page.html_content:
                        current_content = page.html_content.encode()
                    else:
                        current_content = b""

                    if previous_page.html_content:
                        previous_content = previous_page.html_content.encode()
                    else:
                        previous_content = b""

                    current_hash = hashlib.sha256(current_content).hexdigest()
                    previous_hash = hashlib.sha256(previous_content).hexdigest()
                    html_changed = current_hash != previous_hash

                    # Get previous evaluations for this page
                    prev_evals = previous_page.heuristic_evaluations.all()
                    if prev_evals.exists():
                        # Calculate previous score from compliance levels
                        # This gives the LLM context about the overall quality previously assessed
                        level_scores = {
                            "critical": 0,
                            "poor": 3,
                            "fair": 5,
                            "good": 7,
                            "excellent": 10,
                        }
                        prev_scores = [level_scores.get(e.level, 5) for e in prev_evals]
                        previous_score = sum(prev_scores) / len(prev_scores)

                        # Build previous evaluations dict for each heuristic
                        # LLM will use this to maintain consistency if HTML hasn't changed
                        previous_evaluations = {
                            eval.heuristic_id: {
                                "level": eval.level,
                                "problems": eval.problems or "",
                                "html_changed": html_changed,  # Pass this info to LLM
                            }
                            for eval in prev_evals
                        }

            # Prepare screenshot if available
            screenshot_bytes = None
            screenshot_mime_type = None

            if page.screenshot:
                try:
                    screenshot_bytes = page.screenshot.read()
                    # Determine mime type from extension
                    ext = (
                        page.screenshot.name.split(".")[-1].lower()
                        if "." in page.screenshot.name
                        else ""
                    )
                    if ext == "avif":
                        screenshot_mime_type = "image/avif"
                    elif ext in ["jpg", "jpeg"]:
                        screenshot_mime_type = "image/jpeg"
                    else:
                        screenshot_mime_type = "image/png"  # default/fallback
                except Exception as e:
                    logger.warning(
                        f"Failed to read screenshot {page.screenshot.name}: {e}"
                    )

            # Analyze page with LLM (with previous context if available)
            result = llm_provider.analyze_page(
                html_content=page.html_content,
                heuristics=heuristics,
                previous_score=previous_score,
                previous_evaluations=previous_evaluations,
                screenshot_bytes=screenshot_bytes,
                screenshot_mime_type=screenshot_mime_type,
            )

            # Store result for later consolidation
            all_results.append(
                {
                    "path": page.path,
                    "score": result.overall_score,
                    "evaluations": result.evaluations,
                }
            )

            # Save evaluations to database
            for evaluation in result.evaluations:
                HeuristicEvaluation.objects.update_or_create(
                    page=page,
                    heuristic_id=evaluation.heuristic_id,
                    defaults={
                        "level": evaluation.compliance_level,
                        "problems": "\n".join(evaluation.problems_found),
                        "recommendations": "\n".join(evaluation.recommendations),
                    },
                )

            total_score += result.overall_score
            pages_analyzed += 1

        # Generate consolidated executive summary and priorities from all results
        executive_summary = ""
        priorities = []

        if pages_analyzed > 0 and all_results:
            # Build a summary of all findings for the LLM to consolidate
            findings_summary = []
            for result in all_results:
                findings_summary.append(
                    f"Página: {result['path']} (Score: {result['score']}/10)"
                )
                for evaluation in result["evaluations"]:
                    heuristic_name = next(
                        (
                            h["name"]
                            for h in heuristics
                            if h["id"] == evaluation.heuristic_id
                        ),
                        "Unknown",
                    )
                    findings_summary.append(
                        f"  - {heuristic_name}: {evaluation.compliance_level}"
                    )
                    if evaluation.problems_found:
                        findings_summary.append(
                            f"    Problemas: {'; '.join(evaluation.problems_found[:2])}"
                        )  # Limit to first 2
                findings_summary.append("")

            # Ask LLM to generate executive summary and priorities
            consolidation_result = llm_provider.generate_executive_summary(
                findings="\n".join(findings_summary),
                average_score=total_score / pages_analyzed,
                total_pages=pages_analyzed,
            )

            executive_summary = consolidation_result.get("executive_summary", "")
            priorities = consolidation_result.get("priorities", [])

        # Update analysis with average score and consolidated data
        if pages_analyzed > 0:
            analysis.score = str(round(total_score / pages_analyzed, 1))
            analysis.executive_summary = executive_summary
            analysis.priorities = priorities

        # Mark as completed
        analysis.status = Analysis.Status.COMPLETED
        analysis.save(
            update_fields=["status", "score", "executive_summary", "priorities"]
        )

        return {
            "status": "success",
            "message": f"Heuristic analysis completed for {pages_analyzed} pages",
            "analysis_id": analysis_id,
            "average_score": analysis.score,
        }

    except Exception as e:
        # Mark analysis as failed
        analysis = Analysis.objects.get(id=analysis_id)
        analysis.status = Analysis.Status.FAILED
        analysis.error_message = str(e)
        analysis.save(update_fields=["status", "error_message"])

        return {
            "status": "error",
            "message": f"Heuristic analysis failed: {str(e)}",
            "analysis_id": analysis_id,
        }


@shared_task(bind=True)
def run_crawler(
    self,
    analysis_id: int,
    start_url: str,
    ignore_paths: list[str] | None = None,
    enforce_paths: list[str] | None = None,
    agent_name: str | None = None,
    time_between_requests: float = 1.0,
    search_depth: int = 2,
):
    """Run the domain crawler with specified configuration using Playwright."""
    agent_name = agent_name or settings.CRAWLER_USER_AGENT

    try:
        # Get the analysis object
        analysis = Analysis.objects.get(id=analysis_id)
        analysis.status = Analysis.Status.CRAWLING
        analysis.save(update_fields=["status"])
    except Analysis.DoesNotExist:
        return {
            "status": "error",
            "message": f"Analysis with id {analysis_id} does not exist",
        }

    try:
        # Run playwright crawler synchronously via class method
        crawler_result = PlaywrightCrawler.run_crawler(
            analysis_id=analysis_id,
            start_url=start_url,
            ignore_paths=ignore_paths,
            enforce_paths=enforce_paths,
            agent_name=agent_name,
            time_between_requests=time_between_requests,
            search_depth=search_depth,
        )

        if crawler_result.get("status") == "error":
            analysis.status = Analysis.Status.FAILED
            analysis.error_message = crawler_result.get(
                "message", "Unknown crawler error"
            )
            analysis.save(update_fields=["status", "error_message"])
            return crawler_result

    except Exception as e:
        analysis.status = Analysis.Status.FAILED
        analysis.error_message = str(e)
        analysis.save(update_fields=["status", "error_message"])
        return {
            "status": "error",
            "message": f"Crawler failed: {str(e)}",
            "analysis_id": analysis_id,
        }

    # Mark analysis as crawl completed (ready for heuristics analysis)
    analysis.refresh_from_db()
    analysis.status = Analysis.Status.CRAWL_COMPLETED
    analysis.save(update_fields=["status"])

    # Trigger heuristics analysis task
    run_heuristic_analysis.delay(analysis_id)

    return {
        "status": "success",
        "message": f"Crawler executed successfully for {start_url}",
        "start_url": start_url,
        "analysis_id": analysis_id,
    }
