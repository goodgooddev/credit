"""Оценка риска. Только Decimal и целые баллы, без float и без random.

Балл риска — сумма штрафов по факторам (0 — нет риска, 100 — максимум).
Пороги и веса собраны в константах ниже: правила меняются в одном месте.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models import Application, Product, RiskLevel
from app.services.checks import CHECK_NO_HISTORY, CHECK_OK

CENT = Decimal("0.01")

# Уровень риска по баллу: меньше LOW_BELOW — низкий, меньше MEDIUM_BELOW — средний, иначе высокий
LOW_BELOW = 25
MEDIUM_BELOW = 50


def money(value: Decimal) -> str:
    """Деньги в JSON — строкой с копейками, как и в API."""
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def monthly_payment(amount: Decimal, annual_rate_percent: Decimal, term_months: int) -> Decimal:
    """Аннуитетный ежемесячный платёж."""
    if amount <= 0 or annual_rate_percent < 0 or term_months <= 0:
        raise ValueError("Сумма и срок должны быть положительными, ставка — неотрицательной")
    monthly_rate = annual_rate_percent / Decimal(12) / Decimal(100)
    if monthly_rate == 0:
        payment = amount / term_months
    else:
        payment = amount * monthly_rate / (1 - (1 + monthly_rate) ** -term_months)
    return payment.quantize(CENT, rounding=ROUND_HALF_UP)


def level_for(score: int) -> str:
    if score < LOW_BELOW:
        return RiskLevel.LOW.value
    if score < MEDIUM_BELOW:
        return RiskLevel.MEDIUM.value
    return RiskLevel.HIGH.value


def calculate_risk(application: Application, product: Product, check_results: dict) -> dict:
    """Оценка риска по согласованным факторам.

    Возвращает {"score", "level", "factors": [{"code", "points", "message"}], "metrics", "monthly_payment"}.
    Вызывается, только когда проверки доступны (иначе оценивать нечего).
    """
    amount = application.amount
    revenue = application.annual_revenue
    expenses = application.monthly_expenses
    debt = application.existing_debt

    payment = monthly_payment(amount, product.annual_rate, application.term_months)
    debt_payment = application.monthly_debt_payment or Decimal("0")
    net_monthly = revenue / 12 - expenses - debt_payment  # после платежей по существующим кредитам
    coverage = net_monthly / payment if net_monthly > 0 and payment > 0 else None
    debt_to_revenue = debt / revenue if revenue > 0 else None
    amount_to_revenue = amount / revenue if revenue > 0 else None

    factors: list[dict] = []

    def add(code: str, points: int, message: str) -> None:
        if points > 0:
            factors.append({"code": code, "points": points, "message": message})

    # 1. Хватает ли денежного потока на платёж
    # (суммы платежа в текстах нет: итоговый платёж зависит от ставки, см. offered_conditions)
    if coverage is None:
        add(
            "payment_coverage",
            40,
            "Ежемесячные расходы не меньше выручки: платёж по кредиту покрыть нечем",
        )
    elif coverage < 1:
        add(
            "payment_coverage",
            40,
            "Свободный денежный поток меньше ежемесячного платежа по кредиту",
        )
    elif coverage < Decimal("1.3"):
        add(
            "payment_coverage",
            25,
            "Ежемесячный платёж почти равен свободному денежному потоку",
        )
    elif coverage < 2:
        add(
            "payment_coverage",
            10,
            "Запас денежного потока над ежемесячным платежом небольшой",
        )

    # 2. Текущая задолженность относительно выручки
    if debt_to_revenue is None:
        add(
            "debt_to_revenue",
            25 if debt > 0 else 0,
            "Есть задолженность при нулевой выручке",
        )
    elif debt_to_revenue > 1:
        add("debt_to_revenue", 25, "Текущая задолженность больше годовой выручки")
    elif debt_to_revenue > Decimal("0.5"):
        add(
            "debt_to_revenue",
            15,
            "Текущая задолженность больше половины годовой выручки",
        )
    elif debt_to_revenue > Decimal("0.25"):
        add(
            "debt_to_revenue",
            5,
            "Текущая задолженность больше четверти годовой выручки",
        )

    # 3. Размер кредита относительно выручки
    if amount_to_revenue is None or amount_to_revenue > 1:
        add("amount_to_revenue", 15, "Сумма кредита больше годовой выручки")
    elif amount_to_revenue > Decimal("0.5"):
        add("amount_to_revenue", 8, "Сумма кредита больше половины годовой выручки")

    # 4. Возраст бизнеса
    age = check_results["company_age_months"]
    if age < 12:
        add("company_age", 15, "Компании меньше года")
    elif age < 24:
        add("company_age", 8, "Компании меньше двух лет")

    # 5. Кредитная история (недоступность сюда не попадает: это не плохая история)
    history = check_results["credit_history"]
    if history["status"] == CHECK_NO_HISTORY:
        add("no_credit_history", 15, "У компании нет кредитной истории")
    elif history["status"] == CHECK_OK:
        overdue = history["overdue_30d_count"]
        if overdue >= 3:
            add("overdue", 30, f"Просрочки более 30 дней в кредитной истории: {overdue}")
        elif overdue >= 1:
            add("overdue", 15, f"Просрочки более 30 дней в кредитной истории: {overdue}")
        if history["active_loans"] >= 3:
            add(
                "active_loans",
                10,
                f"Много действующих кредитов: {history['active_loans']}",
            )

    # 6. Налоговая задолженность
    if check_results["tax_debt"]["has_debt"]:
        add("tax_debt", 25, "Есть налоговая задолженность")

    score = min(sum(f["points"] for f in factors), 100)
    return {
        "score": score,
        "level": level_for(score),
        "factors": factors,
        "metrics": {
            # жёсткое условие для решения: хватает ли свободного потока хотя бы на сам платёж
            "covers_payment": coverage is not None and coverage >= 1,
            "monthly_payment": money(payment),
            "existing_monthly_debt_payment": money(debt_payment),
            "net_monthly_cash_flow": money(net_monthly),
            "payment_coverage": None if coverage is None else str(coverage.quantize(CENT)),
            "debt_to_revenue": None if debt_to_revenue is None else str(debt_to_revenue.quantize(CENT)),
            "amount_to_revenue": None if amount_to_revenue is None else str(amount_to_revenue.quantize(CENT)),
        },
    }
