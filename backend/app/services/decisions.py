"""Решение по заявке.

Цепочка: validate_application (в роутере, даёт 422) -> run_checks -> calculate_risk
-> make_decision -> save_assessment_and_events. Каждый шаг — отдельная функция.
При повторном рассмотрении создаётся НОВЫЙ Assessment, старые остаются.

Демонстрационные правила, не банковская скоринговая модель:
недоступная проверка -> повтор; налоговый долг / 3+ просрочки -> отказ;
неизвестен платёж по существующему долгу -> запрос сведений;
непокрытый платёж / высокий риск -> отказ; иначе одобрение по ставке продукта.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    Assessment,
    Company,
    Decision,
    EventType,
    Product,
    RiskLevel,
)
from app.services.checks import CHECK_OK, CHECK_TITLES, run_checks
from app.services.events import add_event
from app.services.scoring import calculate_risk, money, monthly_payment

RULES_VERSION = "2026-10-v2"

OVERDUE_REJECT_COUNT = 3  # столько просрочек 30+ дней — автоматический отказ

# Решение -> статус заявки. Недоступной проверки здесь нет: статус остаётся submitted.
STATUS_BY_DECISION = {
    Decision.APPROVED.value: ApplicationStatus.APPROVED.value,
    Decision.REJECTED.value: ApplicationStatus.REJECTED.value,
    Decision.NEEDS_INFO.value: ApplicationStatus.NEEDS_INFO.value,
}


def make_decision(application: Application, product: Product, check_results: dict, risk: dict | None) -> dict:
    """Итог с учётом проверок, риска, условий продукта, суммы и срока.

    Возвращает {"decision", "reasons": [str], "offered_conditions": dict | None}.
    risk=None, если проверки недоступны.
    """
    # 1. Недоступная проверка — это не плохая история и не отказ
    if check_results["unavailable"]:
        names = ", ".join(CHECK_TITLES[name] for name in check_results["unavailable"])
        return {
            "decision": Decision.CHECK_UNAVAILABLE.value,
            "reasons": [
                f"Не удалось выполнить проверки: {names}. Это не отказ и не плохая кредитная история. "
                "Заявка сохранена, обработку можно повторить позже."
            ],
            "offered_conditions": None,
        }

    # 2. Жёсткие причины отказа
    hard_stops: list[str] = []
    if check_results["tax_debt"]["has_debt"]:
        hard_stops.append("Есть налоговая задолженность")
    history = check_results["credit_history"]
    if history["status"] == CHECK_OK and history["overdue_30d_count"] >= OVERDUE_REJECT_COUNT:
        hard_stops.append(f"Просрочки более 30 дней в кредитной истории: {history['overdue_30d_count']}")
    if hard_stops:
        return {
            "decision": Decision.REJECTED.value,
            "reasons": hard_stops,
            "offered_conditions": None,
        }

    # 3. Конкретные сведения, которые клиент может дополнить через PATCH.
    if application.existing_debt > 0 and application.monthly_debt_payment is None:
        return {
            "decision": Decision.NEEDS_INFO.value,
            "reasons": [
                "Укажите ежемесячный платёж по действующим кредитам "
                "(0, если платежей сейчас нет). Ежемесячные расходы указывайте без этих платежей."
            ],
            "requested_fields": ["monthly_debt_payment"],
            "offered_conditions": None,
        }

    # 4. Все сведения получены: проверяем покрытие итогового платежа и риск.
    reject_reasons: list[str] = []
    if not risk["metrics"]["covers_payment"]:
        reject_reasons.append(
            "Свободного денежного потока (выручка за месяц минус расходы и платежи по действующим кредитам) не хватает на ежемесячный платёж по кредиту"
        )
    if risk["level"] == RiskLevel.HIGH.value:
        ordered = sorted(risk["factors"], key=lambda f: -f["points"])
        reject_reasons.append("Высокий риск: " + "; ".join(f["message"] for f in ordered))
    if reject_reasons:
        return {
            "decision": Decision.REJECTED.value,
            "reasons": reject_reasons,
            "offered_conditions": None,
        }

    # 5. На этапе 3 сохраняем ставку продукта. Изменение условий и их принятие — этап 4.
    rate = product.annual_rate
    reasons = [
        "Заявка одобрена на условиях выбранного продукта",
        *(f["message"] for f in risk["factors"]),
    ]
    return {
        "decision": Decision.APPROVED.value,
        "reasons": reasons,
        "offered_conditions": {
            "amount": money(application.amount),
            "term_months": application.term_months,
            "annual_rate": str(rate.quantize(Decimal("0.01"))),
            "monthly_payment": money(monthly_payment(application.amount, rate, application.term_months)),
        },
    }


def save_assessment_and_events(
    db: Session,
    application: Application,
    *,
    inputs: dict,
    check_results: dict,
    risk: dict | None,
    result: dict,
    from_status: str,
) -> Assessment:
    """Сохраняет НОВУЮ оценку, переводит заявку в итоговый статус и пишет историю.

    commit делает вызывающий код: отправка и решение попадают в базу одной транзакцией.
    """
    decision = result["decision"]
    assessment = Assessment(
        check_results={
            "inputs": inputs,
            "checks": check_results,
            "risk": risk,
            "requested_fields": result.get("requested_fields", []),
        },
        risk_score=risk["score"] if risk else None,
        risk_level=risk["level"] if risk else None,
        decision=decision,
        reasons=result["reasons"],
        offered_conditions=result["offered_conditions"],
        rules_version=RULES_VERSION,
    )
    application.assessments.append(assessment)

    # Поля, которые меняет только сервер
    application.status = STATUS_BY_DECISION.get(decision, ApplicationStatus.SUBMITTED.value)
    application.decision = decision
    application.risk_level = assessment.risk_level

    db.flush()  # получаем assessment.id для события
    add_event(
        db,
        application,
        EventType.ASSESSED,
        None,  # решение принимает система
        from_status=from_status,
        to_status=application.status,
        payload={
            "assessment_id": assessment.id,
            "decision": decision,
            "risk_level": assessment.risk_level,
            "risk_score": assessment.risk_score,
            "rules_version": RULES_VERSION,
        },
    )
    return assessment


def review_application(
    db: Session,
    application: Application,
    product: Product,
    company: Company,
    *,
    as_of: date,
) -> Assessment:
    """Прогоняет заявку по всей цепочке и сохраняет результат (без commit).

    Данные уже должны пройти validate_application. `as_of` — дата отправки: от неё зависит
    возраст компании, поэтому повторная обработка даёт тот же результат, что и первая.
    """
    from_status = application.status
    inputs = {
        "product_id": product.id,
        "purpose": application.purpose,
        "monthly_debt_payment": (
            money(application.monthly_debt_payment) if application.monthly_debt_payment is not None else None
        ),
        "product": {
            "annual_rate": str(product.annual_rate),
            "purposes": list(product.purposes),
            "min_amount": money(product.min_amount),
            "max_amount": money(product.max_amount),
            "min_term_months": product.min_term_months,
            "max_term_months": product.max_term_months,
            "is_active": product.is_active,
        },
        "company": {
            "id": company.id,
            "registration_date": company.registration_date.isoformat(),
            "profile": company.profile,
        },
        "amount": money(application.amount),
        "term_months": application.term_months,
        "annual_revenue": money(application.annual_revenue),
        "monthly_expenses": money(application.monthly_expenses),
        "existing_debt": money(application.existing_debt),
        "as_of": as_of.isoformat(),
    }
    check_results = run_checks(company, as_of)
    missing_payment = application.existing_debt > 0 and application.monthly_debt_payment is None
    risk = (
        None if check_results["unavailable"] or missing_payment else calculate_risk(application, product, check_results)
    )
    result = make_decision(application, product, check_results, risk)
    return save_assessment_and_events(
        db,
        application,
        inputs=inputs,
        check_results=check_results,
        risk=risk,
        result=result,
        from_status=from_status,
    )
