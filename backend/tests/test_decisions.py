"""Этап 3: проверки, риск, решение. Три сценария через API + чистые функции."""

from datetime import date

import pytest
from sqlalchemy import delete, select

from app.models import Application, ApplicationEvent, Assessment, Company, User
from tests.conftest import FULL

GOOD_PROFILE = {
    "credit_history": {"overdue_30d_count": 0, "active_loans": 1},
    "tax_debt": False,
}


def company_id_by_name(client, headers, name: str) -> int:
    return next(c["id"] for c in client.get("/companies", headers=headers).json() if name in c["name"])


def submit_new(client, headers, company_id, product_id, **fields) -> dict:
    r = client.post(
        "/applications",
        headers=headers,
        json={"company_id": company_id, "product_id": product_id, **FULL, **fields},
    )
    assert r.status_code == 201, r.text
    r = client.post(f"/applications/{r.json()['id']}/submit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


pytestmark = pytest.mark.integration


# ---------- Три сценария через API ----------
def test_scenario_approve(client, client1, company1_id, product_id):
    app = submit_new(client, client1, company1_id, product_id)
    assert app["status"] == "approved"
    assert app["decision"] == "approved"
    assert app["risk_level"] == "low"
    assessment = app["latest_assessment"]
    assert assessment["risk_score"] == 0
    assert assessment["rules_version"]
    assert assessment["offered_conditions"]["monthly_payment"] == "45959.06"
    # решение и история сохранены в базе, а не только в ответе
    again = client.get(f"/applications/{app['id']}", headers=client1).json()
    assert again["latest_assessment"]["id"] == assessment["id"]
    events = client.get(f"/applications/{app['id']}/events", headers=client1).json()
    assessed = events[-1]
    assert [e["event_type"] for e in events] == ["created", "submitted", "assessed"]
    assert assessed["actor_id"] is None  # решение принимает система
    assert assessed["from_status"] == "submitted"
    assert assessed["to_status"] == "approved"
    assert assessed["payload"]["assessment_id"] == assessment["id"]


def test_scenario_reject(client, client2, product_id):
    company_id = company_id_by_name(client, client2, "СтройРесурс")
    app = submit_new(client, client2, company_id, product_id)
    assert app["status"] == "rejected"
    assert app["risk_level"] == "high"
    assessment = app["latest_assessment"]
    assert assessment["offered_conditions"] is None
    assert any("налогов" in reason for reason in assessment["reasons"])
    assert any("Просрочки" in reason for reason in assessment["reasons"])
    # после отказа заявку не изменить и не отправить снова
    assert client.patch(f"/applications/{app['id']}", headers=client2, json={"amount": "100000"}).status_code == 409
    assert client.post(f"/applications/{app['id']}/submit", headers=client2).status_code == 409


def test_scenario_needs_info_then_resubmit(client, client1, product_id):
    company_id = company_id_by_name(client, client1, "Петров")  # молодой бизнес без кредитной истории
    young = {"annual_revenue": "3000000.00", "monthly_expenses": "100000.00"}
    app = submit_new(client, client1, company_id, product_id, existing_debt="100000.00", **young)
    assert app["status"] == "needs_info"
    first = app["latest_assessment"]
    assert first["offered_conditions"] is None
    assert first["requested_fields"] == ["monthly_debt_payment"]
    assert first["risk_score"] is None

    # клиент дополняет заявку (статус needs_info допускает правки) и отправляет снова
    r = client.patch(
        f"/applications/{app['id']}",
        headers=client1,
        json={"monthly_debt_payment": "10000.00"},
    )
    assert r.status_code == 200
    r = client.post(f"/applications/{app['id']}/submit", headers=client1)
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "approved"
    assert final["latest_assessment"]["id"] != first["id"]

    # прежняя оценка не потеряна: в базе две записи, у первой старое решение
    from app.database import SessionLocal

    with SessionLocal() as db:
        saved = db.scalars(
            select(Assessment).where(Assessment.application_id == app["id"]).order_by(Assessment.id)
        ).all()
        assert [a.decision for a in saved] == ["needs_info", "approved"]
        assert saved[0].check_results["inputs"]["monthly_debt_payment"] is None
        assert saved[1].check_results["inputs"]["monthly_debt_payment"] == "10000.00"

    events = client.get(f"/applications/{app['id']}/events", headers=client1).json()
    assert [e["event_type"] for e in events] == [
        "created",
        "submitted",
        "assessed",
        "updated",
        "submitted",
        "assessed",
    ]
    assert [e["to_status"] for e in events if e["event_type"] == "assessed"] == [
        "needs_info",
        "approved",
    ]


def test_unchanged_resubmit_gives_same_needs_info(client, client1, product_id):
    """Без правок результат тот же (одинаковые данные -> одинаковое решение), но это новая запись оценки."""
    company_id = company_id_by_name(client, client1, "Петров")
    app = submit_new(
        client,
        client1,
        company_id,
        product_id,
        existing_debt="100000.00",
        annual_revenue="3000000.00",
        monthly_expenses="100000.00",
    )
    again = client.post(f"/applications/{app['id']}/submit", headers=client1).json()
    assert again["status"] == "needs_info"
    assert again["latest_assessment"]["reasons"] == app["latest_assessment"]["reasons"]
    assert again["latest_assessment"]["id"] != app["latest_assessment"]["id"]


def test_same_application_data_gives_same_decision(client, client1, company1_id, product_id):
    one = submit_new(client, client1, company1_id, product_id)["latest_assessment"]
    two = submit_new(client, client1, company1_id, product_id)["latest_assessment"]
    for key in (
        "risk_score",
        "risk_level",
        "decision",
        "reasons",
        "offered_conditions",
        "rules_version",
    ):
        assert one[key] == two[key], key


def test_incomplete_submit_stays_draft(client, client1, company1_id):
    r = client.post(
        "/applications",
        headers=client1,
        json={"company_id": company1_id, "amount": "500000"},
    )
    r = client.post(f"/applications/{r.json()['id']}/submit", headers=client1)
    assert r.status_code == 422
    app = client.get(
        f"/applications/{client.get('/applications', headers=client1).json()[0]['id']}",
        headers=client1,
    ).json()
    assert app["status"] == "draft"
    assert app["latest_assessment"] is None  # решение по неполной заявке не создаётся


# ---------- Недоступная проверка и повтор обработки ----------
@pytest.fixture
def company_without_checks():
    """Компания клиента 1 с пустым profile: сервис проверок для неё «недоступен»."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        owner = db.scalars(select(User).where(User.email == "client1@demo.local")).one()
        company = Company(
            owner_id=owner.id,
            name="ООО «Без проверок»",
            inn="7700000999",
            industry="Тест",
            region="Москва",
            registration_date=date(2019, 3, 12),
            employees_count=1,
            profile={},
        )
        db.add(company)
        db.commit()
        company_id = company.id
    yield company_id
    with SessionLocal() as db:  # заявки ссылаются на компанию, поэтому сначала их
        app_ids = select(Application.id).where(Application.company_id == company_id)
        db.execute(delete(Assessment).where(Assessment.application_id.in_(app_ids)))
        db.execute(delete(ApplicationEvent).where(ApplicationEvent.application_id.in_(app_ids)))
        db.execute(delete(Application).where(Application.company_id == company_id))
        db.execute(delete(Company).where(Company.id == company_id))
        db.commit()


def test_unavailable_check_then_reprocess(client, client1, staff, company_without_checks, product_id):
    app = submit_new(client, client1, company_without_checks, product_id)
    # не отказ: заявка остаётся на рассмотрении, есть объяснение, риск не выставлен
    assert app["status"] == "submitted"
    assert app["decision"] == "check_unavailable"
    assert app["risk_level"] is None
    assert "не отказ" in app["latest_assessment"]["reasons"][0]

    # проверки всё ещё недоступны: повтор честно даёт то же самое, но запись оценки новая
    url = f"/applications/{app['id']}/reprocess"
    still = client.post(url, headers=client1).json()
    assert still["status"] == "submitted"
    assert still["latest_assessment"]["id"] != app["latest_assessment"]["id"]

    # «сервис проверок» восстановился -> повторная обработка выносит решение
    from app.database import SessionLocal

    with SessionLocal() as db:
        db.get(Company, company_without_checks).profile = GOOD_PROFILE
        db.commit()
    r = client.post(url, headers=staff)  # повторить может и сотрудник
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    events = client.get(f"/applications/{app['id']}/events", headers=client1).json()
    assert [e["event_type"] for e in events] == [
        "created",
        "submitted",
        "assessed",
        "reprocessed",
        "assessed",
        "reprocessed",
        "assessed",
    ]
    # решение уже вынесено: повторно пересматривать нельзя
    assert client.post(url, headers=client1).status_code == 409


def test_reprocess_rules(client, client1, client2, company1_id, product_id):
    approved = submit_new(client, client1, company1_id, product_id)
    # у заявки есть решение (не check_unavailable) -> 409
    assert client.post(f"/applications/{approved['id']}/reprocess", headers=client1).status_code == 409
    # чужая заявка -> 403, несуществующая -> 404
    assert client.post(f"/applications/{approved['id']}/reprocess", headers=client2).status_code == 403
    assert client.post("/applications/99999/reprocess", headers=client1).status_code == 404
    # черновик повторно обрабатывать нельзя
    draft = client.post("/applications", headers=client1, json={"company_id": company1_id}).json()
    assert client.post(f"/applications/{draft['id']}/reprocess", headers=client1).status_code == 409


def test_invalid_purpose_cannot_be_submitted(client, client1, company1_id, product_id):
    r = client.post(
        "/applications",
        headers=client1,
        json={
            "company_id": company1_id,
            "product_id": product_id,
            **FULL,
            "purpose": "Покупка оборудования",
        },
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    r = client.post(f"/applications/{aid}/submit", headers=client1)
    assert r.status_code == 422
    assert any(e["field"] == "purpose" for e in r.json()["errors"])
    assert client.get(f"/applications/{aid}", headers=client1).json()["latest_assessment"] is None


def test_review_error_rolls_back_entire_submission(client, client1, company1_id, product_id, monkeypatch):
    import app.services.decisions as decisions

    r = client.post(
        "/applications",
        headers=client1,
        json={"company_id": company1_id, "product_id": product_id, **FULL},
    )
    aid = r.json()["id"]
    original = decisions.save_assessment_and_events

    def fail_after_flush(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("simulated storage error")

    monkeypatch.setattr(decisions, "save_assessment_and_events", fail_after_flush)
    with pytest.raises(RuntimeError, match="simulated storage error"):
        client.post(f"/applications/{aid}/submit", headers=client1)
    saved = client.get(f"/applications/{aid}", headers=client1).json()
    assert saved["status"] == "draft"
    assert saved["submitted_at"] is None
    assert saved["latest_assessment"] is None
    assert [e["event_type"] for e in client.get(f"/applications/{aid}/events", headers=client1).json()] == ["created"]


def test_debt_payment_can_change_decision_to_rejection(client, client1, company1_id, product_id):
    a = submit_new(
        client,
        client1,
        company1_id,
        product_id,
        existing_debt="100000",
        monthly_expenses="960000",
    )
    assert a["status"] == "needs_info"
    url = f"/applications/{a['id']}"
    assert client.patch(url, headers=client1, json={"monthly_debt_payment": "20000"}).status_code == 200
    r = client.post(url + "/submit", headers=client1)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_assessment_keeps_product_and_company_snapshot(client, client1, company1_id, product_id):
    from app.database import SessionLocal

    a = submit_new(client, client1, company1_id, product_id)
    with SessionLocal() as db:
        saved = db.get(Assessment, a["latest_assessment"]["id"])
        assert saved.check_results["inputs"]["product"]["annual_rate"] == "18.50"
        assert saved.check_results["inputs"]["company"]["profile"]["tax_debt"] is False
        assert saved.check_results["inputs"]["purpose"] == FULL["purpose"]
