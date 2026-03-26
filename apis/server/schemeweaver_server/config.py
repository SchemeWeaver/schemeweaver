from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    redis_url: str = "redis://localhost:6379"
    use_async_worker: bool = False  # False = sync mode (v1), True = async via ARQ
    model: str = "claude-sonnet-4-6"

    class Config:
        env_file = ".env"


settings = Settings()
