from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from tests.conftest import FULL


def create_draft(client, headers, company_id, **fields):
    r = client.post("/applications", headers=headers, json={"company_id": company_id, **fields})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- Служебные ----------
def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json()["database"] == "ok"


def test_docs_available(client):
    assert client.get("/docs").status_code == 200


# ---------- Авторизация ----------
def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"email": "client1@demo.local", "password": "nope"})
    assert r.status_code == 401


def test_requires_token(client):
    assert client.get("/applications").status_code == 401
    assert client.get("/applications", headers={"Authorization": "Bearer garbage"}).status_code == 401


# ---------- Черновик ----------
def test_partial_draft_persists(client, client1, company1_id):
    draft = create_draft(client, client1, company1_id, amount="250000.50")
    assert draft["status"] == "draft"
    assert draft["term_months"] is None
    again = client.get(f"/applications/{draft['id']}", headers=client1).json()
    assert again["amount"] == "250000.50"  # деньги строкой, без потери точности


def test_negative_amount_gives_clear_error(client, client1, company1_id):
    r = client.post("/applications", headers=client1, json={"company_id": company1_id, "amount": "-5"})
    assert r.status_code == 422
    body = r.json()
    assert body["errors"][0]["field"] == "amount"
    assert "больше 0" in body["errors"][0]["message"]


def test_client_cannot_set_server_fields(client, client1, company1_id):
    draft = create_draft(client, client1, company1_id)
    for forbidden in ({"status": "approved"}, {"risk_level": "low"}, {"decision": "approved"}, {"user_id": 99}):
        r = client.patch(f"/applications/{draft['id']}", headers=client1, json=forbidden)
        assert r.status_code == 422, forbidden
    assert client.get(f"/applications/{draft['id']}", headers=client1).json()["status"] == "draft"


def test_cannot_use_foreign_company(client, client1, client2):
    foreign_company = client.get("/companies", headers=client2).json()[0]["id"]
    r = client.post("/applications", headers=client1, json={"company_id": foreign_company})
    assert r.status_code == 404


# ---------- Права доступа ----------
def test_foreign_application_forbidden(client, client1, client2, company1_id):
    draft = create_draft(client, client1, company1_id)
    url = f"/applications/{draft['id']}"
    assert client.get(url, headers=client2).status_code == 403
    assert client.patch(url, headers=client2, json={"amount": "1000"}).status_code == 403
    assert client.post(f"{url}/submit", headers=client2).status_code == 403
    assert client.get(f"{url}/events", headers=client2).status_code == 403
    assert client.get("/applications", headers=client2).json() == []


def test_staff_access(client, client1, staff, company1_id, product_id):
    draft = create_draft(client, client1, company1_id, product_id=product_id, **FULL)
    # сотрудник видит заявку клиента, но не редактирует
    assert client.get(f"/applications/{draft['id']}", headers=staff).status_code == 200
    assert client.patch(f"/applications/{draft['id']}", headers=staff, json={"amount": "1"}).status_code == 403
    # клиенту список сотрудника недоступен
    assert client.get("/staff/applications", headers=client1).status_code == 403
    # черновики в списке сотрудника по умолчанию скрыты
    assert client.get("/staff/applications", headers=staff).json() == []
    assert len(client.get("/staff/applications?status=draft", headers=staff).json()) == 1


# ---------- Отправка ----------
def test_submit_incomplete_lists_missing_fields(client, client1, company1_id):
    draft = create_draft(client, client1, company1_id, amount="500000")
    r = client.post(f"/applications/{draft['id']}/submit", headers=client1)
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert {"product_id", "term_months", "purpose"} <= fields
    assert "amount" not in fields


def test_submit_checks_product_limits(client, client1, company1_id, product_id):
    draft = create_draft(client, client1, company1_id, product_id=product_id, **{**FULL, "amount": "50000"})
    r = client.post(f"/applications/{draft['id']}/submit", headers=client1)
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "amount"


def test_submit_and_history(client, client1, company1_id, product_id):
    draft = create_draft(client, client1, company1_id, product_id=product_id, **FULL)
    r = client.post(f"/applications/{draft['id']}/submit", headers=client1)
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"
    events = client.get(f"/applications/{draft['id']}/events", headers=client1).json()
    assert [e["event_type"] for e in events] == ["created", "submitted"]
    # после отправки редактировать нельзя
    assert client.patch(f"/applications/{draft['id']}", headers=client1, json={"amount": "1000"}).status_code == 409


def test_double_submit_is_rejected(client, client1, company1_id, product_id):
    draft = create_draft(client, client1, company1_id, product_id=product_id, **FULL)
    url = f"/applications/{draft['id']}/submit"
    assert client.post(url, headers=client1).status_code == 200
    assert client.post(url, headers=client1).status_code == 409
    events = client.get(f"/applications/{draft['id']}/events", headers=client1).json()
    assert [e["event_type"] for e in events].count("submitted") == 1


def test_concurrent_submit_only_one_wins(client, client1, company1_id, product_id):
    """Двойное нажатие: два запроса одновременно — решение должно появиться один раз."""
    draft = create_draft(client, client1, company1_id, product_id=product_id, **FULL)
    url = f"/applications/{draft['id']}/submit"
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(f.result().status_code for f in [pool.submit(client.post, url, headers=client1) for _ in range(2)])
    assert codes == [200, 409]
    events = client.get(f"/applications/{draft['id']}/events", headers=client1).json()
    assert [e["event_type"] for e in events].count("submitted") == 1


# ---------- Seed ----------
def test_seed_is_idempotent_and_keeps_applications(client, client1, company1_id):
    from app.database import SessionLocal
    from app.models import Application, Company, Product, User
    from app.seed import seed

    draft = create_draft(client, client1, company1_id)
    with SessionLocal() as db:
        before = [db.scalar(select(func.count()).select_from(m)) for m in (User, Company, Product)]
        seed(db)
        seed(db)
        after = [db.scalar(select(func.count()).select_from(m)) for m in (User, Company, Product)]
        assert before == after
        assert db.get(Application, draft["id"]) is not None
