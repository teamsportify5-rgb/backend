"""Persist in-app notification history alongside FCM push delivery."""
import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models import NotificationLog, User
from app.push_delivery import try_notify_user


def record_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    body: str,
    notification_type: str = "general",
    sent_by_user_id: Optional[int] = None,
    data: Optional[dict] = None,
) -> NotificationLog:
    log = NotificationLog(
        user_id=user_id,
        sent_by_user_id=sent_by_user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        data_json=json.dumps(data) if data else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def notify_user_and_record(
    db: Session,
    user: User,
    *,
    title: str,
    body: str,
    notification_type: str = "general",
    sent_by_user_id: Optional[int] = None,
    data: Optional[dict] = None,
) -> bool:
    """Save to notification history and attempt FCM push. Returns push success."""
    record_notification(
        db,
        user_id=user.id,
        title=title,
        body=body,
        notification_type=notification_type,
        sent_by_user_id=sent_by_user_id,
        data=data,
    )
    return try_notify_user(user, title, body, data)
