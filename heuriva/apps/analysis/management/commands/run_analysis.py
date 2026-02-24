from django.conf import settings
from django.core.management.base import BaseCommand

from heuriva.apps.analysis.models import Analysis, Project
from heuriva.apps.analysis.tasks import run_crawler


class Command(BaseCommand):
    help = "Run crawler analysis for a project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            required=True,
            help="ID of the project to analyze",
        )
        parser.add_argument(
            "--depth-limit",
            type=int,
            default=2,
            help="Maximum crawl depth (default: 2)",
        )
        parser.add_argument(
            "--download-delay",
            type=int,
            default=1,
            help="Delay between requests in seconds (default: 1)",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="run_async",
            help="Run crawler asynchronously using Celery",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"]
        depth_limit = options["depth_limit"]
        download_delay = options["download_delay"]
        run_async = options["run_async"]

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Project with ID {project_id} does not exist")
            )
            return

        # Create a new analysis
        analysis = Analysis.objects.create(
            project=project,
            score=0,  # Will be updated after heuristics evaluation
            heuristics_group_id=1,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Created Analysis ID: {analysis.id} for {project.name}")
        )

        # Prepare crawler parameters
        crawler_params = {
            "analysis_id": analysis.id,
            "start_url": project.url,
            "search_depth": depth_limit,
            "time_between_requests": download_delay,
            "agent_name": settings.CRAWLER_USER_AGENT,
        }

        if run_async:
            task = run_crawler.delay(**crawler_params)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Crawler task queued with ID: {task.id}\n"
                    f"Use 'celery -A heuriva inspect active' to check status"
                )
            )
            return

        # Run synchronously
        self.stdout.write(self.style.WARNING("Running crawler synchronously..."))
        self.stdout.write(
            self.style.WARNING("This may take a while. Press Ctrl+C to cancel.")
        )

        try:
            result = run_crawler(**crawler_params)
            if result.get("status") == "success":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Crawler completed successfully!\n"
                        f"Analysis ID: {analysis.id}\n"
                        f"Check the admin panel for results."
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Crawler failed: {result.get('message', 'Unknown Error')}"
                    )
                )
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nCrawler interrupted by user"))
            self.stdout.write(
                self.style.WARNING(
                    f"Analysis ID {analysis.id} may have partial results"
                )
            )
