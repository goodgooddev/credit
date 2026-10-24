"""Проверки заявки.

Сейчас реализован validate_application() — он нужен уже при отправке.
run_checks() (проверка компании и кредитной истории) — задача 22 октября.
"""

from app.models import Application, Product

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


def validate_application(application: Application, product: Product | None) -> list[dict]:
    """Полнота и допустимость данных перед отправкой.

    Возвращает список ошибок [{"field", "message"}]; пустой список = всё хорошо.
    Черновик может быть неполным, поэтому эта проверка вызывается только при отправке.
    """
    errors: list[dict] = []
    for field, message in REQUIRED_FOR_SUBMIT.items():
        if getattr(application, field) is None:
            errors.append({"field": field, "message": message})

    if product is not None:
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


def run_checks(application: Application) -> dict:
    """TODO (22 октября): локальная проверка компании и кредитной истории.

    Результат детерминированный: одинаковые данные -> одинаковый ответ, без random.
    Недоступность проверки НЕ равна плохой кредитной истории.
    """
    raise NotImplementedError
