"""Проверки заявки.

validate_application() — полнота и допустимость данных, вызывается при отправке (и повторной обработке).
run_checks() — локальная проверка компании и кредитной истории по синтетическим данным
из companies.profile. Внешних сервисов нет, поэтому результат всегда воспроизводим.
"""

from datetime import date

from app.models import Application, Company, Product

# поле -> человеческое название для сообщения об ошибке
REQUIRED_FOR_SUBMIT = {
    "product_id": "Выберите продукт",
    "amount": "Укажите сумму",
    "term_months": "Укажите срок",
    "purpose": "Укажите цель кредита",
    "annual_revenue": "Укажите годовую выручку",
    "monthly_expenses": "Укажите ежемесячные расходы",
    "existing_debt": "Укажите текущую задолженность (0, если нет)",
}

# Статусы одной проверки
CHECK_OK = "ok"
CHECK_NO_HISTORY = "no_history"  # данные получены: у компании истории нет (это не плохая история)
CHECK_UNAVAILABLE = "unavailable"  # данных получить не удалось (это тоже не плохая история)

# Человеческие названия проверок для объяснения клиенту
CHECK_TITLES = {
    "credit_history": "кредитная история",
    "tax_debt": "налоговая задолженность",
}


def validate_application(application: Application, product: Product | None) -> list[dict]:
    """Полнота и допустимость данных перед отправкой.

    Возвращает список ошибок [{"field", "message"}]; пустой список = всё хорошо.
    Черновик может быть неполным, поэтому эта проверка вызывается только при отправке.
    """
    errors: list[dict] = []
    for field, message in REQUIRED_FOR_SUBMIT.items():
        if getattr(application, field) is None:
            errors.append({"field": field, "message": message})

    if application.purpose is not None and not application.purpose.strip():
        errors.append({"field": "purpose", "message": "Укажите цель кредита"})
    if application.product_id is not None and product is None:
        errors.append({"field": "product_id", "message": "Продукт не найден"})
    if product is not None:
        if application.purpose and application.purpose.strip() and application.purpose.strip() not in product.purposes:
            errors.append(
                {
                    "field": "purpose",
                    "message": "Выберите допустимую цель выбранного продукта",
                }
            )
        if not product.is_active:
            errors.append({"field": "product_id", "message": "Продукт больше не доступен"})
        if application.amount is not None and not (product.min_amount <= application.amount <= product.max_amount):
            errors.append(
                {
                    "field": "amount",
                    "message": f"Сумма по продукту: от {product.min_amount} до {product.max_amount}",
                }
            )
        if application.term_months is not None and not (
            product.min_term_months <= application.term_months <= product.max_term_months
        ):
            errors.append(
                {
                    "field": "term_months",
                    "message": f"Срок по продукту: от {product.min_term_months} до {product.max_term_months} мес.",
                }
            )
    return errors


def _age_in_months(registered: date, as_of: date) -> int:
    months = (as_of.year - registered.year) * 12 + (as_of.month - registered.month)
    if as_of.day < registered.day:
        months -= 1
    return max(months, 0)


def run_checks(company: Company, as_of: date) -> dict:
    """Локальная проверка компании и кредитной истории.

    Результат детерминированный: одинаковые данные -> одинаковый ответ, без random.
    `as_of` — дата отправки заявки (а не «сегодня»), поэтому повторная обработка даёт тот же результат.

    Как читаем companies.profile (так же устроен seed):
      "credit_history": {...}  -> история есть (ok)
      "credit_history": null   -> истории нет (no_history), это НЕ плохая история
      ключа нет                -> сервис проверки недоступен (unavailable), это НЕ плохая история
      "tax_debt": true/false   -> долг есть/нет; ключа нет -> проверка недоступна
    """
    profile = company.profile if isinstance(company.profile, dict) else {}

    if "credit_history" not in profile:
        credit_history = {"status": CHECK_UNAVAILABLE}
    elif profile["credit_history"] is None:
        credit_history = {"status": CHECK_NO_HISTORY}
    else:
        raw = profile["credit_history"]
        fields = ("overdue_30d_count", "active_loans")
        if not isinstance(raw, dict) or any(type(raw.get(k)) is not int or raw[k] < 0 for k in fields):
            credit_history = {
                "status": CHECK_UNAVAILABLE,
                "reason": "Некорректный ответ проверки",
            }
        else:
            credit_history = {"status": CHECK_OK, **{k: raw[k] for k in fields}}

    if type(profile.get("tax_debt")) is not bool:
        tax_debt = {"status": CHECK_UNAVAILABLE, "has_debt": None}
    else:
        tax_debt = {"status": CHECK_OK, "has_debt": profile["tax_debt"]}

    unavailable = [
        name
        for name, result in (("credit_history", credit_history), ("tax_debt", tax_debt))
        if result["status"] == CHECK_UNAVAILABLE
    ]
    return {
        "company_age_months": _age_in_months(company.registration_date, as_of),
        "credit_history": credit_history,
        "tax_debt": tax_debt,
        "unavailable": unavailable,
    }
