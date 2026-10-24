"""Зависимости FastAPI: кто делает запрос и какая у него роль."""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False, description="Токен из POST /auth/login")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Требуется авторизация",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_client(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Доступно только клиентам")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Доступно только сотрудникам")
    return user
