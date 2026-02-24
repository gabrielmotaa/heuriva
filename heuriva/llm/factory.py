"""
Factory for creating LLM provider instances.
Uses singleton pattern to ensure rate limiter is shared across tasks.
"""

from django.conf import settings

from .gemini_provider import GeminiProvider
from .interface import LLMProvider

# Singleton instance - shared across all tasks in the same worker process
_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider instance (singleton).

    This ensures the same provider instance (and its rate limiter) is reused
    across all tasks in the same worker process, making rate limiting effective.

    Returns:
        LLMProvider instance based on settings.LLM_PROVIDER

    Raises:
        ValueError: If provider is not supported or not configured
    """
    global _provider_instance

    # Return existing instance if already created
    if _provider_instance is not None:
        return _provider_instance

    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY must be set in environment to use Gemini provider"
            )
        _provider_instance = GeminiProvider(model=settings.GEMINI_MODEL)
        return _provider_instance

    # Future providers can be added here:
    # elif provider == "openai":
    #     return OpenAIProvider()
    # elif provider == "anthropic":
    #     return AnthropicProvider()

    raise ValueError(
        f"Unsupported LLM provider: {provider}. Supported providers: gemini"
    )
