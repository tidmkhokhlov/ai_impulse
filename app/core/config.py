from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db/postgres"
    tg_bot_token: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
