from .base import LLMProvider
from .anthropic import AnthropicProvider
from .openai_compat import OpenAICompatProvider


def make_provider(
    provider: str,
    model: str,
    api_key: str = "",
    base_url: str | None = None,
) -> LLMProvider:
    """
    Factory for LLM providers.

    provider: "anthropic" | "openai" | "ollama"
    model:    e.g. "claude-sonnet-4-6", "gpt-4o", "qwen2.5:14b"
    api_key:  required for anthropic/openai, ignored for ollama
    base_url: override API base (set automatically for ollama)
    """
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)

    if provider == "ollama":
        return OpenAICompatProvider(
            model=model,
            api_key="ollama",
            base_url=base_url or "http://localhost:11434/v1",
        )

    if provider == "openai":
        return OpenAICompatProvider(model=model, api_key=api_key, base_url=base_url)

    raise ValueError(f"Unknown provider '{provider}'. Choose: anthropic, openai, ollama")
