"""Описание таблиц. Деньги везде NUMERIC(14, 2) -> Decimal в Python, никакого float."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(enum.StrEnum):
    CLIENT = "client"
    STAFF = "staff"


class ApplicationStatus(enum.StrEnum):
    DRAFT = "draft"  # черновик, клиент редактирует
    SUBMITTED = "submitted"  # отправлена, ждёт обработки
    NEEDS_INFO = "needs_info"  # нужны уточнения, клиент дополняет и отправляет снова
    APPROVED = "approved"  # одобрена
    REJECTED = "rejected"  # отказ
    COUNTER_OFFER = "counter_offer"  # предложены изменённые условия
    ACCEPTED = "accepted"  # клиент принял условия


# Статусы, в которых клиент может менять поля и отправлять заявку
EDITABLE_STATUSES = (ApplicationStatus.DRAFT, ApplicationStatus.NEEDS_INFO)


class Decision(enum.StrEnum):
    """Итог рассмотрения (applications.decision и assessments.decision)."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"
    # Проверку выполнить не удалось. Это НЕ отказ: заявка остаётся submitted, обработку можно повторить
    CHECK_UNAVAILABLE = "check_unavailable"


class RiskLevel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventType(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    SUBMITTED = "submitted"
    ASSESSED = "assessed"  # система вынесла решение (создана запись Assessment)
    REPROCESSED = "reprocessed"  # повторный запуск обработки после недоступной проверки


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default=UserRole.CLIENT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    companies: Mapped[list["Company"]] = relationship(back_populates="owner")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str] = mapped_column(String(12), unique=True)
    industry: Mapped[str] = mapped_column(String(255))
    region: Mapped[str] = mapped_column(String(255))
    registration_date: Mapped[date] = mapped_column(Date)
    employees_count: Mapped[int] = mapped_column(Integer, default=0)
    # Синтетические данные бизнеса для проверок: кредитная история, налоговые долги и т.п.
    profile: Mapped[dict] = mapped_column(JSON, default=dict)

    owner: Mapped[User] = relationship(back_populates="companies")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    purposes: Mapped[list] = mapped_column(JSON, default=list)  # допустимые цели кредита
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    max_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    min_term_months: Mapped[int] = mapped_column(Integer)
    max_term_months: Mapped[int] = mapped_column(Integer)
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # % годовых
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("amount IS NULL OR amount > 0", name="ck_applications_amount_positive"),
        CheckConstraint(
            "term_months IS NULL OR term_months > 0",
            name="ck_applications_term_positive",
        ),
        CheckConstraint(
            "annual_revenue IS NULL OR annual_revenue >= 0",
            name="ck_applications_revenue_nonneg",
        ),
        CheckConstraint(
            "monthly_expenses IS NULL OR monthly_expenses >= 0",
            name="ck_applications_expenses_nonneg",
        ),
        CheckConstraint(
            "existing_debt IS NULL OR existing_debt >= 0",
            name="ck_applications_debt_nonneg",
        ),
        CheckConstraint(
            "monthly_debt_payment IS NULL OR monthly_debt_payment >= 0",
            name="ck_applications_debt_payment_nonneg",
        ),
        Index("ix_applications_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # владелец заявки
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))

    # Поля, которые заполняет клиент (в черновике все необязательные)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    term_months: Mapped[int | None] = mapped_column(Integer)
    purpose: Mapped[str | None] = mapped_column(String(500))
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    monthly_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    existing_debt: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    monthly_debt_payment: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    # Поля, которые меняет ТОЛЬКО сервер (клиент передать их не может)
    status: Mapped[str] = mapped_column(String(32), default=ApplicationStatus.DRAFT.value, index=True)
    risk_level: Mapped[str | None] = mapped_column(String(16))
    decision: Mapped[str | None] = mapped_column(String(32))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[Company] = relationship()
    product: Mapped[Product | None] = relationship()
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="application", order_by="Assessment.id")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application", order_by="ApplicationEvent.id"
    )

    @property
    def latest_assessment(self) -> "Assessment | None":
        return self.assessments[-1] if self.assessments else None


class Assessment(Base):
    """Результат рассмотрения. При повторном рассмотрении добавляется НОВАЯ запись."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    check_results: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str | None] = mapped_column(String(16))
    decision: Mapped[str | None] = mapped_column(String(32))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    offered_conditions: Mapped[dict | None] = mapped_column(JSON)
    rules_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="assessments")

    @property
    def requested_fields(self) -> list[str]:
        return (self.check_results or {}).get("requested_fields", [])


class ApplicationEvent(Base):
    """История действий и переходов заявки."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # NULL = система
    event_type: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="events")
