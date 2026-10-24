from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_staff
from app.models import Application, ApplicationStatus, Company, User
from app.schemas import ApplicationOut, StaffApplicationOut

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/applications", response_model=list[StaffApplicationOut])
def staff_applications(
    status: ApplicationStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Все заявки для сотрудника. Без фильтра status черновики не показываются."""
    stmt = (
        select(Application, Company.name, User.email)
        .join(Company, Company.id == Application.company_id)
        .join(User, User.id == Application.user_id)
        .order_by(Application.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        stmt = stmt.where(Application.status == status.value)
    else:
        stmt = stmt.where(Application.status != ApplicationStatus.DRAFT.value)

    return [
        StaffApplicationOut(
            **ApplicationOut.model_validate(application).model_dump(),
            company_name=company_name,
            owner_email=owner_email,
        )
        for application, company_name, owner_email in db.execute(stmt).all()
    ]
