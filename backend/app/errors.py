"""Единый формат ошибок: {"detail": "...", "errors": [{"field": "...", "message": "..."}]}."""

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _message(err: dict) -> str:
    kind, ctx = err["type"], err.get("ctx", {})
    if kind == "missing":
        return "Поле обязательно"
    if kind == "greater_than":
        return f"Значение должно быть больше {ctx.get('gt')}"
    if kind == "greater_than_equal":
        return f"Значение не может быть меньше {ctx.get('ge')}"
    if kind == "less_than_equal":
        return f"Значение не может быть больше {ctx.get('le')}"
    if kind == "extra_forbidden":
        return "Это поле нельзя передавать"
    if kind in ("decimal_max_places", "decimal_whole_digits", "decimal_max_digits"):
        return "Слишком большое число или больше 2 знаков после запятой"
    if kind.endswith("_parsing") or kind.endswith("_type") or kind == "int_from_float":
        return "Некорректное значение"
    return err["msg"]


class FieldValidationError(Exception):
    """Бизнес-ошибка с привязкой к полям (например, заявка заполнена не полностью)."""

    def __init__(self, errors: list[dict], detail: str = "Проверьте поля запроса"):
        self.errors = errors
        self.detail = detail


def validation_error_response(errors: list[dict], detail: str = "Проверьте поля запроса") -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})


async def field_validation_handler(_: Request, exc: FieldValidationError) -> JSONResponse:
    return validation_error_response(exc.errors, exc.detail)


async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        loc = err["loc"]
        if loc and loc[0] in ("body", "query", "path"):
            loc = loc[1:]
        errors.append(
            {"field": ".".join(str(part) for part in loc), "message": _message(jsonable_encoder(err))}
        )
    return validation_error_response(errors)
