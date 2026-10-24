from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_client
from app.models import Company, User
from app.schemas import CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
def my_companies(user: User = Depends(require_client), db: Session = Depends(get_db)):
    """Компании текущего клиента. Нужны, чтобы выбрать company_id при создании заявки."""
    return db.scalars(select(Company).where(Company.owner_id == user.id).order_by(Company.id)).all()
