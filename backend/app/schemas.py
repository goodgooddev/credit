"""Схемы запросов и ответов. Здесь же — «контракт» для фронтенда.

Деньги в JSON передаются СТРОКОЙ ("500000.00"), чтобы не терять точность.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ApplicationStatus, UserRole

Money = Decimal  # для читаемости: сумма в рублях, максимум 2 знака после запятой


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Каталог и компании ----------
class ProductOut(ORMModel):
    id: int
    code: str
    name: str
    description: str
    purposes: list[str]
    min_amount: Money
    max_amount: Money
    min_term_months: int
    max_term_months: int
    annual_rate: Decimal


class CompanyOut(ORMModel):
    id: int
    name: str
    inn: str
    industry: str
    region: str
    registration_date: date
    employees_count: int


# ---------- Заявки ----------
class ApplicationFields(BaseModel):
    """Поля, которые клиент вправе передавать. Любое другое поле (status, risk_level,
    decision, user_id, role...) запрещено: extra="forbid" вернёт 422."""

    model_config = ConfigDict(extra="forbid")

    product_id: int | None = None
    amount: Money | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    term_months: int | None = Field(default=None, gt=0, le=600)
    purpose: str | None = Field(default=None, min_length=1, max_length=500)
    annual_revenue: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    monthly_expenses: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    existing_debt: Money | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class ApplicationCreate(ApplicationFields):
    company_id: int


class ApplicationUpdate(ApplicationFields):
    """PATCH: передаются только изменяемые поля."""


class ApplicationOut(ORMModel):
    id: int
    company_id: int
    product_id: int | None
    amount: Money | None
    term_months: int | None
    purpose: str | None
    annual_revenue: Money | None
    monthly_expenses: Money | None
    existing_debt: Money | None
    status: ApplicationStatus
    risk_level: str | None
    decision: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentOut(ORMModel):
    id: int
    risk_score: int | None
    risk_level: str | None
    decision: str | None
    reasons: list[str]
    offered_conditions: dict | None
    rules_version: str
    created_at: datetime


class ApplicationDetail(ApplicationOut):
    company: CompanyOut
    product: ProductOut | None
    latest_assessment: AssessmentOut | None


class StaffApplicationOut(ApplicationOut):
    company_name: str
    owner_email: str


class EventOut(ORMModel):
    id: int
    event_type: str
    from_status: str | None
    to_status: str | None
    actor_id: int | None
    payload: dict
    created_at: datetime


# ---------- Ошибки ----------
class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    detail: str
    errors: list[FieldError] | None = None
