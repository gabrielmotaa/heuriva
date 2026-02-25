"""
Google Gemini provider implementation.
"""

from google import genai
from google.genai import types

from .interface import (
    ConsolidatedAnalysisResult,
    HeuristicAnalysisResult,
    LLMProvider,
)
from .prompts import EXECUTIVE_SUMMARY_PROMPT, HEURISTIC_ANALYSIS_PROMPT
from .rate_limiter import RateLimiter


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini provider.

        Args:
            model: Gemini model to use (default: gemini-2.5-flash)
        """
        self.client = genai.Client()
        self.model = model
        self.rate_limiter = RateLimiter()

    def analyze_page(
        self,
        html_content: str,
        heuristics: list[dict],
        previous_score: float | None = None,
        previous_evaluations: dict[int, dict] | None = None,
        screenshot_bytes: bytes | None = None,
        screenshot_mime_type: str | None = None,
    ) -> HeuristicAnalysisResult:
        """
        Analyze page using Gemini.

        Args:
            html_content: HTML content to analyze
            heuristics: List of dicts with 'id', 'name', 'description'
            previous_score: Score from previous analysis (if exists)
            previous_evaluations: Previous evaluations by heuristic_id (if exists)
            screenshot_bytes: Screenshot image bytes of the page
            screenshot_mime_type: MIME type of the screenshot (e.g., 'image/png')

        Returns:
            HeuristicAnalysisResult
        """
        # Build heuristics section for prompt
        heuristics_text = "\n\n".join(
            [f"{h['id']}. **{h['name']}**: {h['description']}" for h in heuristics]
        )

        # Build previous analysis context if available
        previous_context = ""
        html_changed_info = ""

        if previous_score is not None and previous_evaluations:
            # Check if HTML changed (all evaluations should have same value)
            html_changed = any(
                eval.get("html_changed", True) for eval in previous_evaluations.values()
            )

            if not html_changed:
                html_changed_info = """
⚠️ **HTML NÃO MUDOU**: O conteúdo HTML é IDÊNTICO à análise anterior.
   → Você DEVE usar EXATAMENTE os mesmos níveis de conformidade
   → Você DEVE manter o score dentro de ±0.2 pontos
   → Variações não justificadas são ERROS
"""
            else:
                html_changed_info = """
ℹ️ **HTML MUDOU**: O conteúdo HTML é DIFERENTE da análise anterior.
   → Use os níveis anteriores como referência base
   → Ajuste apenas onde o HTML mudou justificar
   → Mantenha consistência onde o HTML não mudou
"""

            previous_context = f"""

# ⚠️ ANÁLISE ANTERIOR DETECTADA - MODO DE CONSISTÊNCIA ATIVADO

{html_changed_info}

**Score da análise anterior**: {previous_score:.1f}/10

**Níveis de conformidade anteriores**:
"""
            for heuristic in heuristics:
                h_id = heuristic["id"]
                if h_id in previous_evaluations:
                    prev_eval = previous_evaluations[h_id]
                    previous_context += (
                        f"\n- **{heuristic['name']}**: {prev_eval['level']}"
                    )
                    if prev_eval.get("problems"):
                        problems_preview = (
                            prev_eval["problems"][:200] + "..."
                            if len(prev_eval["problems"]) > 200
                            else prev_eval["problems"]
                        )
                        previous_context += (
                            f"\n  Problemas identificados: {problems_preview}"
                        )

            previous_context += """

# 🎯 REGRAS OBRIGATÓRIAS DE CONSISTÊNCIA

Você DEVE seguir estas regras ESTRITAMENTE:

1. **Se HTML NÃO MUDOU**: Use EXATAMENTE os mesmos níveis e score (±0.2)
   - Não invente novos problemas em HTML idêntico
   - Não melhore ou piore avaliações arbitrariamente
   - Variações aleatórias são INACEITÁVEIS

2. **Se HTML MUDOU**: Mantenha consistência base
   - Use os níveis anteriores como ponto de partida
   - Só altere onde o HTML realmente mudou
   - Variação de score máxima: ±1.0 ponto (exceto mudanças drásticas)

3. **NUNCA mencione** que está usando uma análise anterior
   - Não diga "conforme análise anterior" ou similar
   - Responda como se fosse uma avaliação independente

⚠️ **ATENÇÃO**: Seu objetivo é CONSISTÊNCIA, não "melhorar" avaliações anteriores!
"""

        prompt = HEURISTIC_ANALYSIS_PROMPT.format(
            previous_context=previous_context,
            heuristics_text=heuristics_text,
            html_content=html_content,
        )

        contents = [prompt]
        if screenshot_bytes and screenshot_mime_type:
            contents.append(
                types.Part.from_bytes(
                    data=screenshot_bytes,
                    mime_type=screenshot_mime_type,
                )
            )

        # Apply rate limiting before making API call
        self.rate_limiter.wait_if_needed()

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": HeuristicAnalysisResult,
            },
        )

        # Parse Gemini response directly to HeuristicAnalysisResult
        return response.parsed  # type: ignore

    def generate_executive_summary(
        self, findings: str, average_score: float, total_pages: int
    ) -> dict:
        """
        Generate consolidated executive summary and priorities.

        Args:
            findings: Summary of findings from all pages
            average_score: Average score across all pages
            total_pages: Total number of pages analyzed

        Returns:
            Dictionary with 'executive_summary' and 'priorities'
        """

        prompt = EXECUTIVE_SUMMARY_PROMPT.format(
            total_pages=total_pages,
            average_score=average_score,
            findings=findings,
        )

        # Apply rate limiting before making API call
        self.rate_limiter.wait_if_needed()

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ConsolidatedAnalysisResult,
            },
        )

        # Return as dict for compatibility with task
        result = response.parsed  # type: ignore
        return {
            "executive_summary": result.executive_summary,
            "priorities": result.priorities,
        }
