from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import FieldValidationError, field_validation_handler, request_validation_handler
from app.routers import applications, auth, companies, health, products, staff

app = FastAPI(
    title="Умный кредитный кабинет — API",
    version="0.1.0",
    description=(
        "Бэкенд кейса «Умный кредитный кабинет предпринимателя».\n\n"
        "Как авторизоваться в Swagger: выполните `POST /auth/login`, скопируйте `access_token`, "
        "нажмите **Authorize** и вставьте его."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(FieldValidationError, field_validation_handler)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(staff.router)
