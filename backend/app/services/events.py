"""Запись истории заявки."""

from sqlalchemy.orm import Session

from app.models import Application, ApplicationEvent, EventType, User


def add_event(
    db: Session,
    application: Application,
    event_type: EventType,
    actor: User | None,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict | None = None,
) -> ApplicationEvent:
    """Добавляет событие в текущую транзакцию (commit делает вызывающий код)."""
    event = ApplicationEvent(
        application_id=application.id,
        actor_id=actor.id if actor else None,
        event_type=event_type.value,
        from_status=from_status,
        to_status=to_status,
        payload=payload or {},
    )
    db.add(event)
    return event
