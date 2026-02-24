from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class HeuristicEvaluation(BaseModel):
    """Single heuristic evaluation result."""

    heuristic_id: int = Field(description="ID da heurística avaliada")
    is_satisfied: bool = Field(description="Se a heurística foi atendida/satisfeita")
    compliance_level: Literal["excellent", "good", "fair", "poor", "critical"] = Field(
        description="Nível de conformidade: excellent (excelente), good (bom), fair (regular), poor (ruim), critical (crítico)"
    )
    problems_found: list[str] = Field(
        description="Lista de problemas específicos encontrados relacionados a esta heurística"
    )
    recommendations: list[str] = Field(
        description="Lista de recomendações práticas e acionáveis para melhorar"
    )
    code_examples: list[str] = Field(
        default=[], description="Trechos de código HTML problemáticos (se aplicável)"
    )


class HeuristicAnalysisResult(BaseModel):
    """Complete heuristic analysis result for a page."""

    overall_score: float = Field(
        ge=0,
        le=10,
        description="Pontuação geral de 0 a 10 baseada em todas as heurísticas",
    )
    evaluations: list[HeuristicEvaluation] = Field(
        description="Lista de avaliações, uma para cada heurística"
    )
    executive_summary: str = Field(
        description="Resumo executivo dos principais problemas e pontos positivos encontrados"
    )
    priorities: list[str] = Field(
        description="Top 3-5 melhorias prioritárias ordenadas por impacto na experiência do usuário"
    )


class ConsolidatedAnalysisResult(BaseModel):
    """Consolidated analysis result from multiple pages."""

    executive_summary: str = Field(
        description="Resumo executivo consolidado de 2-4 parágrafos identificando padrões, problemas recorrentes e aspectos positivos em todas as páginas analisadas"
    )
    priorities: list[str] = Field(
        description="Lista de 5-10 melhorias prioritárias ordenadas por impacto na experiência do usuário, considerando todas as páginas"
    )


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Allows easy switching between different LLM services.
    """

    @abstractmethod
    def analyze_page(
        self,
        html_content: str,
        heuristics: list[dict],
        previous_score: float | None = None,
        previous_evaluations: dict[int, dict] | None = None,
    ) -> HeuristicAnalysisResult:
        """
        Analyze a page's HTML content against provided heuristics.

        Args:
            html_content: The HTML content to analyze
            heuristics: List of heuristics with 'id', 'name', and 'description'
            previous_score: Score from previous analysis of the same page (if exists)
            previous_evaluations: Dict mapping heuristic_id to previous evaluation data
                                 with 'level' and 'problems' (if exists)

        Returns:
            HeuristicAnalysisResult with analysis results
        """
        pass

    @abstractmethod
    def generate_executive_summary(
        self, findings: str, average_score: float, total_pages: int
    ) -> dict:
        """
        Generate consolidated executive summary and priorities from all page analyses.

        Args:
            findings: Summary of findings from all analyzed pages
            average_score: Average score across all pages
            total_pages: Total number of pages analyzed

        Returns:
            Dictionary with 'executive_summary' (str) and 'priorities' (list[str])
        """
        pass
