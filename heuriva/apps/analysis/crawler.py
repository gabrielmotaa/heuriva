import concurrent.futures
import logging
import time
from io import BytesIO
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image
from playwright.sync_api import TimeoutError, sync_playwright
from protego import Protego

from heuriva.apps.analysis.models import Analysis, Page

logger = logging.getLogger(__name__)


def optimize_screenshot(screenshot_bytes: bytes) -> bytes:
    """Optimize a PNG screenshot and convert it to AVIF."""
    image = Image.open(BytesIO(screenshot_bytes))
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        if "A" in image.mode:
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    output = BytesIO()
    # Use AVIF for better compression with good quality
    image.save(output, format="AVIF", quality=80)
    return output.getvalue()


class PlaywrightCrawler:
    """Crawler implementation using sync_playwright."""

    @classmethod
    def run_crawler(
        cls,
        analysis_id: int,
        start_url: str,
        ignore_paths: list[str] | None = None,
        enforce_paths: list[str] | None = None,
        agent_name: str | None = None,
        time_between_requests: float = 1.0,
        search_depth: int = 2,
        respect_robots_txt: bool = True,
    ):
        crawler = cls(
            analysis_id=analysis_id,
            start_url=start_url,
            ignore_paths=ignore_paths,
            enforce_paths=enforce_paths,
            agent_name=agent_name,
            time_between_requests=time_between_requests,
            search_depth=search_depth,
            respect_robots_txt=respect_robots_txt,
        )
        return crawler.run()

    def __init__(
        self,
        analysis_id: int,
        start_url: str,
        ignore_paths: list[str] | None = None,
        enforce_paths: list[str] | None = None,
        agent_name: str | None = None,
        time_between_requests: float = 1.0,
        search_depth: int = 2,
        respect_robots_txt: bool = True,
    ):
        self.analysis_id = analysis_id
        self.start_url = start_url
        self.ignore_paths = ignore_paths or []
        self.enforce_paths = enforce_paths or []
        self.agent_name = agent_name or settings.CRAWLER_USER_AGENT
        self.time_between_requests = time_between_requests
        self.search_depth = search_depth
        self.respect_robots_txt = respect_robots_txt

        self.analysis = Analysis.objects.get(id=self.analysis_id)
        self.project = self.analysis.project

        parsed_start = urlparse(self.start_url)
        self.base_domain = parsed_start.netloc
        self.base_url = f"{parsed_start.scheme}://{parsed_start.netloc}"

        self.queue = [(self.start_url, 0)]
        self.visited = set()

        self.enforce_urls = []
        for ep in self.enforce_paths:
            if not ep.startswith("/"):
                ep = "/" + ep
            self.enforce_urls.append(urljoin(self.start_url, ep))

        # Threadpool for ORM operations
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.page_instance = None
        self.robots_parser = None

    def _should_ignore(self, path: str) -> bool:
        for p in self.ignore_paths:
            if p and path.startswith(p):
                return True
        return False

    def _is_allowed_by_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt rules."""
        if not self.respect_robots_txt or self.robots_parser is None:
            return True

        return self.robots_parser.can_fetch(self.agent_name, url)

    def _fetch_robots_txt(self, page):
        """Fetch and parse robots.txt from the base URL."""
        if not self.respect_robots_txt:
            return

        robots_url = urljoin(self.base_url, "robots.txt")
        try:
            response = page.goto(robots_url, wait_until="load", timeout=10000)
            if response and response.status == 200:
                robots_content = page.content()
                self.robots_parser = Protego.parse(robots_content)
                logger.info(f"Loaded robots.txt from {robots_url}")
            else:
                logger.info(f"No robots.txt found at {robots_url}, allowing all URLs")
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt: {e}, allowing all URLs")

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()

    def _save_page_to_db(
        self,
        path: str,
        html_content: str,
        screenshot: bytes | None,
        screenshot_format: str,
    ):
        page, _ = Page.objects.update_or_create(
            analysis=self.analysis,
            path=path,
            defaults={"html_content": html_content},
        )

        if screenshot:
            filename = f"screenshot_{self.analysis.id}_{path.replace('/', '_')}.{screenshot_format}"
            if filename.startswith(f"screenshot_{self.analysis.id}__"):
                filename = filename.replace(
                    f"screenshot_{self.analysis.id}__",
                    f"screenshot_{self.analysis.id}_index_",
                )
            page.screenshot.save(filename, ContentFile(screenshot), save=True)

            if path == "/":
                self.project.homepage_screenshot.save(
                    filename, ContentFile(screenshot), save=True
                )

    def _process_url(self, url: str, current_depth: int = 0, is_enforced: bool = False):
        try:
            # Use networkidle to wait until the network is quiet
            response = self.page_instance.goto(url, wait_until="load", timeout=30000)
            if not response or response.status >= 400:
                logger.warning(
                    f"Failed to fetch {url}: Status {response.status if response else 'Unknown'}"
                )
                return

            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                logger.debug(f"Ignoring non-html url: {url}")
                return

            html_content = self.page_instance.content()
            screenshot_bytes = self.page_instance.screenshot(full_page=True)

            try:
                optimized_screenshot = optimize_screenshot(screenshot_bytes)
                screenshot_format = "avif"
            except Exception as e:
                logger.error(f"Failed to optimize screenshot: {e}")
                optimized_screenshot = screenshot_bytes
                screenshot_format = "png"

            parsed_url = urlparse(url)
            path = parsed_url.path or "/"

            # Save to database in a separate thread
            self.thread_pool.submit(
                self._save_page_to_db,
                path,
                html_content,
                optimized_screenshot,
                screenshot_format,
            ).result()

            if not is_enforced and (
                self.search_depth == 0 or current_depth < self.search_depth
            ):
                # Execute JS to get all link hrefs
                links = self.page_instance.eval_on_selector_all(
                    "a[href]", "elements => elements.map(el => el.href)"
                )
                for link in links:
                    link_norm = self._normalize_url(link)
                    link_parsed = urlparse(link_norm)

                    if link_parsed.netloc == self.base_domain:
                        if link_norm not in self.visited and not any(
                            q[0] == link_norm for q in self.queue
                        ):
                            # Check if URL is allowed by robots.txt before adding to queue
                            if self._is_allowed_by_robots_txt(link_norm):
                                self.queue.append((link_norm, current_depth + 1))
                            else:
                                logger.debug(f"URL blocked by robots.txt: {link_norm}")

        except TimeoutError:
            logger.error(f"Timeout crawling {url}")
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
        finally:
            # Clean up page resources after processing
            if self.page_instance:
                self.page_instance.close()

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.agent_name)

            # Fetch and parse robots.txt if needed
            if self.respect_robots_txt:
                temp_page = context.new_page()
                self._fetch_robots_txt(temp_page)
                temp_page.close()

            while self.queue:
                current_url, depth = self.queue.pop(0)
                norm_url = self._normalize_url(current_url)

                if norm_url in self.visited:
                    continue

                parsed_current = urlparse(norm_url)
                path = parsed_current.path or "/"

                if self._should_ignore(path) and norm_url not in self.enforce_urls:
                    continue

                # Check robots.txt before processing (unless it's an enforced URL)
                if (
                    norm_url not in self.enforce_urls
                    and not self._is_allowed_by_robots_txt(norm_url)
                ):
                    logger.debug(f"URL blocked by robots.txt: {norm_url}")
                    continue

                self.visited.add(norm_url)
                logger.info(f"Crawling {norm_url} (depth: {depth})")

                # Create a new page for each URL to avoid memory accumulation
                self.page_instance = context.new_page()
                self._process_url(norm_url, current_depth=depth, is_enforced=False)
                time.sleep(self.time_between_requests)

            # Process enforce_paths if not visited
            for eu in self.enforce_urls:
                norm_eu = self._normalize_url(eu)
                if norm_eu not in self.visited:
                    logger.info(f"Crawling enforced path: {norm_eu}")
                    self.visited.add(norm_eu)

                    self.page_instance = context.new_page()
                    self._process_url(norm_eu, current_depth=0, is_enforced=True)
                    time.sleep(self.time_between_requests)

            browser.close()
            self.thread_pool.shutdown()

        if not Page.objects.filter(analysis=self.analysis).exists():
            return {
                "status": "error",
                "message": "Nenhuma página pôde ser acessada a partir da URL fornecida. Verifique o link e tente novamente.",
            }

        return {"status": "success"}
