from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    redis_url: str = "redis://localhost:6379"
    model: str = "claude-sonnet-4-6"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
