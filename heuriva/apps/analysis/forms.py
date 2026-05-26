from django import forms
from django.conf import settings

from heuriva.apps.heuristics.models import HeuristicGroup


class AnalysisCreateForm(forms.Form):
    # Required fields
    heuristics_group = forms.ModelChoiceField(
        queryset=HeuristicGroup.objects.all(),
        required=True,
        error_messages={
            "required": "Selecione um conjunto de heurísticas.",
            "invalid_choice": "Conjunto de heurísticas inválido.",
        },
    )

    # Crawler configuration
    start_path = forms.CharField(
        max_length=500,
        required=False,
        initial="/",
        widget=forms.TextInput(attrs={"placeholder": "/"}),
        label="Caminho inicial",
    )

    ignore_paths = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Ex: /login\n/admin\n/checkout",
                "rows": 3,
            }
        ),
        help_text="Lista de caminhos para ignorar, um por linha.",
        label="Caminhos para ignorar (opcional)",
    )

    enforce_paths = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Ex: /contato\n/sobre",
                "rows": 3,
            }
        ),
        help_text="Lista de caminhos para forçar acesso, um por linha.",
        label="Caminhos para forçar (opcional)",
    )

    user_agent = forms.CharField(
        max_length=200,
        required=False,
        initial=settings.CRAWLER_USER_AGENT,
        widget=forms.TextInput(attrs={"placeholder": "HeurivaCrawler/1.0"}),
        label="User Agent",
    )

    download_delay = forms.FloatField(
        required=False,
        initial=1.0,
        min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.1", "min": "0"}),
        label="Tempo entre requisições (s)",
    )

    depth_limit = forms.IntegerField(
        required=False,
        initial=2,
        min_value=0,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0"}),
        label="Profundidade máxima de busca",
    )

    respect_robots_txt = forms.BooleanField(
        required=False,
        initial=True,
        label="Respeitar robots.txt",
        help_text="Se ativado, o crawler respeitará as restrições definidas no arquivo robots.txt do site.",
    )

    max_pages = forms.ChoiceField(
        choices=[
            (10, "10 páginas"),
            (20, "20 páginas"),
            (30, "30 páginas"),
            (40, "40 páginas"),
            (50, "50 páginas"),
        ],
        initial=30,
        required=True,
        label="Máximo de páginas",
        help_text="Número máximo de páginas a serem coletadas.",
    )

    def _parse_paths(self, text: str) -> list[str]:
        if not text:
            return []
        # Split by lines and remove empty lines and whitespace
        return [line.strip() for line in text.split("\n") if line.strip()]

    def get_crawler_config(self, project_url: str) -> dict:
        """Build the crawler configuration dictionary from form data."""
        data = self.cleaned_data

        # Construct the full start URL
        start_path = data.get("start_path", "/")
        if not start_path.startswith("/"):
            start_path = "/" + start_path

        # Remove trailing slash from project URL
        base_url = project_url.rstrip("/")
        start_url = base_url + start_path

        config = {
            "start_url": start_url,
            "ignore_paths": self._parse_paths(data.get("ignore_paths", "")),
            "enforce_paths": self._parse_paths(data.get("enforce_paths", "")),
            "time_between_requests": data.get("download_delay", 1.0),
            "agent_name": data.get("user_agent") or settings.CRAWLER_USER_AGENT,
            "search_depth": data.get("depth_limit", 2),
            "respect_robots_txt": data.get("respect_robots_txt", True),
            "max_pages": int(data.get("max_pages", 30)),
        }

        return config
