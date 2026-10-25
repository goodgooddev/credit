"""Этап 3: проверки, риск, решение. Три сценария через API + чистые функции."""

from datetime import date
from decimal import Decimal

import pytest

from app.models import Application, Company, Product
from app.services.checks import run_checks
from app.services.decisions import make_decision
from app.services.scoring import calculate_risk, monthly_payment

AS_OF = date(2026, 10, 25)
PRODUCT = Product(id=1, annual_rate=Decimal("18.50"))
GOOD_PROFILE = {
    "credit_history": {"overdue_30d_count": 0, "active_loans": 1},
    "tax_debt": False,
}


def application(**fields) -> Application:
    values = {
        "amount": Decimal("500000"),
        "term_months": 12,
        "annual_revenue": Decimal("12000000"),
        "monthly_expenses": Decimal("600000"),
        "existing_debt": Decimal("0"),
        **fields,
    }
    return Application(**values)


def review(app: Application, profile: dict, registered: date = date(2019, 3, 12)) -> dict:
    """Вся цепочка без БД: run_checks -> calculate_risk -> make_decision."""
    company = Company(profile=profile, registration_date=registered)
    checks = run_checks(company, AS_OF)
    risk = (
        None
        if checks["unavailable"] or (app.existing_debt > 0 and app.monthly_debt_payment is None)
        else calculate_risk(app, PRODUCT, checks)
    )
    return make_decision(app, PRODUCT, checks, risk) | {"risk": risk, "checks": checks}


# ---------- Чистые функции (без БД) ----------
def test_monthly_payment_matches_annuity_formula():
    # 500 000 ₽, 18.5% годовых, 12 месяцев: эталон посчитан отдельно по формуле аннуитета
    assert monthly_payment(Decimal("500000"), Decimal("18.50"), 12) == Decimal("45959.06")
    assert monthly_payment(Decimal("120000"), Decimal("0"), 12) == Decimal("10000.00")  # нулевая ставка


def test_same_input_same_result():
    one = review(application(), GOOD_PROFILE)
    two = review(application(), GOOD_PROFILE)
    assert one == two


def test_good_company_is_approved_with_conditions():
    result = review(application(), GOOD_PROFILE)
    assert result["decision"] == "approved"
    assert result["risk"]["level"] == "low"
    assert result["offered_conditions"] == {
        "amount": "500000.00",
        "term_months": 12,
        "annual_rate": "18.50",
        "monthly_payment": "45959.06",
    }


def test_tax_debt_is_rejected_with_reason():
    result = review(application(), {**GOOD_PROFILE, "tax_debt": True})
    assert result["decision"] == "rejected"
    assert any("налогов" in r for r in result["reasons"])
    assert result["offered_conditions"] is None


def test_three_overdues_is_rejected_but_two_is_not():
    two = review(
        application(),
        {**GOOD_PROFILE, "credit_history": {"overdue_30d_count": 2, "active_loans": 1}},
    )
    three = review(
        application(),
        {**GOOD_PROFILE, "credit_history": {"overdue_30d_count": 3, "active_loans": 1}},
    )
    assert two["decision"] == "approved"  # 15 баллов: низкий риск
    assert three["decision"] == "rejected"


def test_payment_not_covered_is_rejected():
    # выручка 1 млн/мес, расходы 990 тыс -> свободно 10 тыс при платеже ~46 тыс
    result = review(application(monthly_expenses=Decimal("990000")), GOOD_PROFILE)
    assert result["risk"]["metrics"]["payment_coverage"] == "0.22"
    assert result["risk"]["level"] == "medium"  # по баллам только 40, но платить нечем — жёсткий отказ
    assert result["decision"] == "rejected"
    assert "не хватает" in result["reasons"][0]


def test_payment_covered_exactly_is_not_hard_stop():
    # свободный поток ровно равен платежу (покрытие 1.00): ещё не отказ, но 25 баллов штрафа
    app = application(monthly_expenses=Decimal("1000000") - Decimal("45959.06"))
    result = review(app, GOOD_PROFILE)
    assert result["risk"]["metrics"]["covers_payment"] is True
    assert result["decision"] == "approved"


def test_zero_revenue_does_not_crash():
    result = review(
        application(annual_revenue=Decimal("0"), monthly_expenses=Decimal("0")),
        GOOD_PROFILE,
    )
    assert result["decision"] == "rejected"  # платёж покрыть нечем
    assert result["risk"]["metrics"]["debt_to_revenue"] is None


def test_medium_risk_keeps_product_rate():
    # 3 действующих кредита (+10) и платёж почти равен потоку (+25) = 35 -> средний риск
    # свободно 1 000 000 - 945 000 = 55 000 при платеже ~45 959: покрытие 1.20
    profile = {
        "credit_history": {"overdue_30d_count": 0, "active_loans": 3},
        "tax_debt": False,
    }
    result = review(application(monthly_expenses=Decimal("945000")), profile)
    assert result["risk"]["score"] == 35
    assert result["risk"]["level"] == "medium"
    assert result["decision"] == "approved"
    assert result["offered_conditions"]["annual_rate"] == "18.50"  # изменение условий относится к этапу 4


def test_missing_debt_payment_requests_specific_information():
    app = application(existing_debt=Decimal("100000"))
    result = review(app, GOOD_PROFILE)
    assert result["decision"] == "needs_info"
    assert result["requested_fields"] == ["monthly_debt_payment"]
    app.monthly_debt_payment = Decimal("10000")
    assert review(app, GOOD_PROFILE)["decision"] == "approved"


def test_unavailable_check_is_not_bad_history():
    for profile in ({}, {"tax_debt": False}, {"credit_history": None}):
        result = review(application(), profile)
        assert result["decision"] == "check_unavailable", profile
        assert result["risk"] is None  # оценивать по неполным данным не пытаемся
        assert "не отказ" in result["reasons"][0]


@pytest.mark.parametrize(
    "profile",
    [
        {"credit_history": {}, "tax_debt": False},
        {"credit_history": "timeout", "tax_debt": False},
        {
            "credit_history": {"overdue_30d_count": -1, "active_loans": 0},
            "tax_debt": False,
        },
        {"credit_history": GOOD_PROFILE["credit_history"], "tax_debt": "false"},
        {"credit_history": GOOD_PROFILE["credit_history"], "tax_debt": None},
        ["unexpected"],
    ],
)
def test_invalid_check_data_is_unavailable(profile):
    result = review(application(), profile)
    assert result["decision"] == "check_unavailable"
    assert result["risk"] is None


def test_existing_payments_are_deducted():
    result = review(
        application(
            existing_debt=Decimal("100000"),
            monthly_debt_payment=Decimal("20000"),
            monthly_expenses=Decimal("960000"),
        ),
        GOOD_PROFILE,
    )
    assert result["decision"] == "rejected"
    assert result["risk"]["metrics"]["net_monthly_cash_flow"] == "20000.00"


def test_offered_payment_is_the_payment_actually_checked():
    result = review(application(monthly_expenses=Decimal("954040.94")), GOOD_PROFILE)
    assert result["decision"] == "approved"
    assert result["offered_conditions"]["monthly_payment"] == result["risk"]["metrics"]["monthly_payment"]
    assert Decimal(result["offered_conditions"]["monthly_payment"]) <= Decimal(
        result["risk"]["metrics"]["net_monthly_cash_flow"]
    )
    result = review(application(monthly_expenses=Decimal("954040.95")), GOOD_PROFILE)
    assert result["decision"] == "rejected"


def test_no_history_is_not_automatic_rejection():
    assert review(application(), {"credit_history": None, "tax_debt": False})["decision"] == "approved"


@pytest.mark.parametrize("score,level", [(24, "low"), (25, "medium"), (49, "medium"), (50, "high")])
def test_risk_boundaries(score, level):
    from app.services.scoring import level_for

    assert level_for(score) == level


def test_schema_normalizes_purpose_and_rejects_blanks():
    from pydantic import ValidationError
    from app.schemas import ApplicationUpdate

    assert ApplicationUpdate(purpose="  Закупка товара  ").purpose == "Закупка товара"
    with pytest.raises(ValidationError):
        ApplicationUpdate(purpose="  ")
    with pytest.raises(ValidationError):
        ApplicationUpdate(monthly_debt_payment="-1")


def test_missing_product_and_invalid_purpose_are_rejected():
    from app.services.checks import validate_application

    app = application(product_id=1, purpose="Покупка оборудования")
    assert any(e["field"] == "product_id" for e in validate_application(app, None))
    product = Product(
        id=1,
        annual_rate=Decimal("18.50"),
        is_active=True,
        min_amount=Decimal("100000"),
        max_amount=Decimal("5000000"),
        min_term_months=3,
        max_term_months=36,
        purposes=["Закупка товара"],
    )
    assert any(e["field"] == "purpose" for e in validate_application(app, product))
