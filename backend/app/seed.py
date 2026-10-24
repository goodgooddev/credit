"""Заполнение тестовыми данными. Запуск: `python -m app.seed`.

Безопасно запускать сколько угодно раз:
- пользователи создаются, только если их ещё нет (пароль существующих не трогаем);
- компании и продукты обновляются по ключу (ИНН / код), поэтому правки текстов от Матвея
  достаточно внести сюда и перезапустить;
- заявки, события и оценки НЕ удаляются и НЕ изменяются.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Company, Product, User, UserRole
from app.security import hash_password

# ---- Данные. TODO: содержание примеров предоставляет Матвей — заменить заглушки ниже ----

USERS = [
    {"email": "client1@demo.local", "full_name": "Иван Петров", "role": UserRole.CLIENT},
    {"email": "client2@demo.local", "full_name": "Мария Соколова", "role": UserRole.CLIENT},
    {"email": "staff@demo.local", "full_name": "Анна Кузнецова (сотрудник банка)", "role": UserRole.STAFF},
]

COMPANIES = [
    {
        "owner_email": "client1@demo.local",
        "inn": "7700000001",
        "name": "ООО «Ромашка-Торг»",
        "industry": "Розничная торговля",
        "region": "Москва",
        "registration_date": date(2019, 3, 12),
        "employees_count": 14,
        # Хорошая кредитная история — для сценария «одобрение»
        "profile": {"credit_history": {"overdue_30d_count": 0, "active_loans": 1}, "tax_debt": False},
    },
    {
        "owner_email": "client1@demo.local",
        "inn": "7700000002",
        "name": "ИП Петров И. С.",
        "industry": "Общественное питание",
        "region": "Московская область",
        "registration_date": date(2024, 6, 1),
        "employees_count": 3,
        # Молодой бизнес без истории — для сценария «запрос уточнений»
        "profile": {"credit_history": None, "tax_debt": False},
    },
    {
        "owner_email": "client2@demo.local",
        "inn": "7700000003",
        "name": "ООО «СтройРесурс»",
        "industry": "Строительство",
        "region": "Санкт-Петербург",
        "registration_date": date(2016, 9, 20),
        "employees_count": 42,
        # Просрочки и налоговый долг — для сценария «отказ»
        "profile": {"credit_history": {"overdue_30d_count": 4, "active_loans": 3}, "tax_debt": True},
    },
]

PRODUCTS = [
    {
        "code": "working_capital",
        "name": "Оборотный кредит",
        "description": "На пополнение оборотных средств: закупка товара, сырья, текущие расходы.",
        "purposes": ["Закупка товара", "Пополнение оборотных средств", "Выплата зарплат"],
        "min_amount": Decimal("100000.00"),
        "max_amount": Decimal("5000000.00"),
        "min_term_months": 3,
        "max_term_months": 36,
        "annual_rate": Decimal("18.50"),
    },
    {
        "code": "investment",
        "name": "Кредит на развитие",
        "description": "На покупку оборудования, ремонт помещений, открытие новой точки.",
        "purposes": ["Покупка оборудования", "Ремонт и аренда помещения", "Открытие новой точки"],
        "min_amount": Decimal("500000.00"),
        "max_amount": Decimal("15000000.00"),
        "min_term_months": 12,
        "max_term_months": 60,
        "annual_rate": Decimal("16.90"),
    },
]


def seed(db: Session) -> None:
    password = get_settings().seed_password

    users: dict[str, User] = {}
    for data in USERS:
        user = db.scalars(select(User).where(User.email == data["email"])).first()
        if user is None:
            user = User(
                email=data["email"],
                full_name=data["full_name"],
                role=data["role"].value,
                password_hash=hash_password(password),
            )
            db.add(user)
        users[data["email"]] = user
    db.flush()

    for data in COMPANIES:
        fields = {k: v for k, v in data.items() if k not in ("owner_email", "inn")}
        company = db.scalars(select(Company).where(Company.inn == data["inn"])).first()
        if company is None:
            db.add(Company(inn=data["inn"], owner_id=users[data["owner_email"]].id, **fields))
        else:
            for key, value in fields.items():
                setattr(company, key, value)

    for data in PRODUCTS:
        fields = {k: v for k, v in data.items() if k != "code"}
        product = db.scalars(select(Product).where(Product.code == data["code"])).first()
        if product is None:
            db.add(Product(code=data["code"], **fields))
        else:
            for key, value in fields.items():
                setattr(product, key, value)

    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("seed: OK")
