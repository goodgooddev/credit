from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_client
from app.errors import FieldValidationError
from app.models import (
    EDITABLE_STATUSES,
    Application,
    ApplicationStatus,
    Company,
    EventType,
    Product,
    User,
    UserRole,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationOut,
    ApplicationUpdate,
    EventOut,
)
from app.services.checks import validate_application
from app.services.events import add_event

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_application(db: Session, application_id: int, user: User, *, lock: bool = False) -> Application:
    """Находит заявку и проверяет, что она принадлежит пользователю (сотрудник видит все).

    lock=True берёт блокировку строки (SELECT ... FOR UPDATE): два одновременных запроса
    к одной заявке выполняются по очереди. Это защита от двойной отправки.
    """
    stmt = select(Application).where(Application.id == application_id)
    if lock:
        stmt = stmt.with_for_update()
    application = db.scalars(stmt).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if user.role != UserRole.STAFF and application.user_id != user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return application


def _ensure_editable(application: Application) -> None:
    if application.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Заявка в статусе «{application.status}» не может быть изменена или отправлена повторно",
        )


def _check_product(db: Session, product_id: int | None) -> None:
    if product_id is None:
        return
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise FieldValidationError([{"field": "product_id", "message": "Такого продукта нет"}])


@router.post("", response_model=ApplicationDetail, status_code=201)
def create_application(
    data: ApplicationCreate,
    user: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Создать черновик. Обязателен только company_id, остальное можно заполнить позже."""
    company = db.get(Company, data.company_id)
    if company is None or company.owner_id != user.id:
        # Не различаем «нет компании» и «чужая компания», чтобы не раскрывать её существование
        raise HTTPException(status_code=404, detail="Компания не найдена")
    fields = data.model_dump(exclude={"company_id"}, exclude_unset=True)
    _check_product(db, fields.get("product_id"))

    application = Application(
        user_id=user.id, company_id=company.id, status=ApplicationStatus.DRAFT.value, **fields
    )
    db.add(application)
    db.flush()  # получаем application.id
    add_event(
        db,
        application,
        EventType.CREATED,
        user,
        to_status=ApplicationStatus.DRAFT.value,
        payload={"company_id": company.id},
    )
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[ApplicationOut])
def list_my_applications(
    status: ApplicationStatus | None = None,
    user: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Заявки текущего клиента, новые сверху."""
    stmt = select(Application).where(Application.user_id == user.id).order_by(Application.id.desc())
    if status is not None:
        stmt = stmt.where(Application.status == status.value)
    return db.scalars(stmt).all()


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Заявка с компанией, продуктом и последним результатом рассмотрения."""
    return _get_application(db, application_id, user)


@router.patch("/{application_id}", response_model=ApplicationDetail)
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    user: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Изменить разрешённые поля (только в статусах draft и needs_info)."""
    application = _get_application(db, application_id, user, lock=True)
    _ensure_editable(application)

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return application
    _check_product(db, changes.get("product_id"))

    for field, value in changes.items():
        setattr(application, field, value)
    add_event(db, application, EventType.UPDATED, user, payload={"fields": sorted(changes)})
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/submit", response_model=ApplicationDetail)
def submit_application(
    application_id: int,
    user: User = Depends(require_client),
    db: Session = Depends(get_db),
):
    """Отправить заявку. Повторная отправка -> 409, второго решения не появится.

    ВАЖНО: пока решение не реализовано (этап 3), заявка переходит в статус `submitted`.
    """
    application = _get_application(db, application_id, user, lock=True)
    _ensure_editable(application)

    product = db.get(Product, application.product_id) if application.product_id else None
    errors = validate_application(application, product)
    if errors:
        raise FieldValidationError(errors, "Заявка заполнена не полностью")

    previous_status = application.status
    application.status = ApplicationStatus.SUBMITTED.value
    application.submitted_at = datetime.now(UTC)
    add_event(
        db,
        application,
        EventType.SUBMITTED,
        user,
        from_status=previous_status,
        to_status=application.status,
    )
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}/events", response_model=list[EventOut])
def application_events(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """История заявки: что и когда происходило."""
    return _get_application(db, application_id, user).events
