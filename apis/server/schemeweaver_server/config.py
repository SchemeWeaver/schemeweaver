from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Provider selection
    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-6"

    # API keys (only required for the selected provider)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Optional base URL override (e.g. point ollama at a remote host)
    llm_base_url: str | None = None

    redis_url: str = "redis://localhost:6379"
    use_async_worker: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
