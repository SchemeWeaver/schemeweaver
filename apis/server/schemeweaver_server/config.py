from pathlib import Path
from pydantic_settings import BaseSettings

# Repo root is three levels up from this file (apis/server/schemeweaver_server/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # API keys — presence of a key enables that provider
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Ollama base URL (no /v1 suffix)
    ollama_base_url: str = "http://localhost:11434"

    redis_url: str = "redis://localhost:6379"
    use_async_worker: bool = False

    # Directory where test_generate.py saves diagram output
    data_out_dir: Path = _REPO_ROOT / "data" / "out"

    # Path to the model registry JSON
    models_registry: Path = _REPO_ROOT / "config" / "models.json"

    class Config:
        env_file = ".env"


settings = Settings()
