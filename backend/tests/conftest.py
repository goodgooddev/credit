"""Тесты работают с НАСТОЯЩИМ PostgreSQL (не SQLite): так проверяются и миграции.

Запуск:  TEST_DATABASE_URL=postgresql+psycopg://credit_app:пароль@localhost:5432/credit_test pytest
Тестовая база должна быть пустой/отдельной — таблицы очищаются между тестами.
"""

import os

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
if TEST_DB:
    # Должно быть выставлено ДО импорта приложения
    os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-32b")

def pytest_collection_modifyitems(config, items):
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL не задан")
    for item in items:
        item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def _database():
    if not TEST_DB:
        yield
        return
    # Защита: схема тестовой базы стирается целиком, на рабочую базу это направлять нельзя
    assert TEST_DB.rsplit("/", 1)[-1].endswith("_test"), "имя тестовой БД должно заканчиваться на _test"

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from app.database import SessionLocal, engine
    from app.seed import seed

    # Чистая схема через те же миграции, что и в проде
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.upgrade(cfg, "head")
    with SessionLocal() as db:
        seed(db)
    yield


@pytest.fixture(autouse=True)
def _clean_applications(_database):
    if not TEST_DB:
        yield
        return
    from sqlalchemy import text

    from app.database import engine

    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE assessments, application_events, applications RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _login(client, email: str) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": "demo12345"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def client1(client):
    return _login(client, "client1@demo.local")


@pytest.fixture
def client2(client):
    return _login(client, "client2@demo.local")


@pytest.fixture
def staff(client):
    return _login(client, "staff@demo.local")


@pytest.fixture
def company1_id(client, client1) -> int:
    return client.get("/companies", headers=client1).json()[0]["id"]


@pytest.fixture
def product_id(client) -> int:
    return client.get("/products").json()[0]["id"]


FULL = {
    "amount": "500000.00",
    "term_months": 12,
    "purpose": "Закупка товара",
    "annual_revenue": "12000000.00",
    "monthly_expenses": "600000.00",
    "existing_debt": "0",
}
