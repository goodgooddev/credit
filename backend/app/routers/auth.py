from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import DUMMY_HASH, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Вход под тестовым пользователем. Дальше передавать `Authorization: Bearer <token>`."""
    user = db.scalars(select(User).where(User.email == data.email.strip().lower())).first()
    # Проверяем хеш даже если пользователя нет — ответ не выдаёт, существует ли email
    password_ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return TokenResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Кто я: удобно фронтенду после перезагрузки страницы."""
    return user
