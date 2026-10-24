"""Подключение к PostgreSQL через обычный (синхронный) SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().sqlalchemy_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Базовый класс всех моделей (таблиц)."""


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: одна сессия БД на один HTTP-запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
