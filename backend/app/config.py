"""Настройки приложения. Всё берётся из переменных окружения (см. .env.example)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # extra="ignore": в окружении контейнера есть и чужие переменные, они не мешают
    model_config = SettingsConfigDict(extra="ignore")

    # Подключение к PostgreSQL. В Docker Compose DB_HOST = "db" (имя сервиса), НЕ localhost.
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "credit"
    db_user: str = "credit_app"
    db_password: str = ""

    # Полный URL имеет приоритет (используется в тестах)
    database_url: str | None = None

    # Подпись JWT-токенов. В реальном окружении обязательно заменить.
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 12 * 60

    # Пароль для тестовых пользователей, которых создаёт seed.py
    seed_password: str = "demo12345"

    # Адреса фронтенда, которым разрешены запросы из браузера (через запятую)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        # URL.create сам экранирует спецсимволы в пароле
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
