from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from firebase_admin import messaging

from app.database import get_db
from app.models import User, NotificationLog
from app.schemas import NotificationLogResponse
from app.auth import get_current_user
from app.firebase_app import ensure_firebase_initialized
from app.push_delivery import ensure_string_data, send_notification_to_token
from app.notification_history import record_notification, notify_user_and_record

router = APIRouter()


class NotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[dict] = None


class NotificationResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None


def _send_token_or_http(fcm_token: str, title: str, body: str, data: Optional[dict] = None) -> str:
    try:
        return send_notification_to_token(fcm_token, title, body, data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        ) from e


@router.get("/history", response_model=List[NotificationLogResponse])
async def get_notification_history(
    scope: str = Query("mine", description="'mine' or 'all' (admin only)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Notification inbox. Users see their own; admin can list all."""
    query = db.query(NotificationLog)
    if scope == "all":
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can view all notification history",
            )
    else:
        query = query.filter(NotificationLog.user_id == current_user.id)

    return (
        query.order_by(NotificationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.patch("/history/{notification_id}/read", response_model=NotificationLogResponse)
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(NotificationLog).filter(NotificationLog.id == notification_id).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if log.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    log.is_read = True
    db.commit()
    db.refresh(log)
    return log


@router.patch("/history/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = (
        db.query(NotificationLog)
        .filter(NotificationLog.user_id == current_user.id, NotificationLog.is_read.is_(False))
        .update({NotificationLog.is_read: True})
    )
    db.commit()
    return {"message": f"Marked {updated} notification(s) as read"}


@router.post("/user/{user_id}", response_model=NotificationResponse)
async def notify_user(
    user_id: int,
    notification: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a notification to a specific user by user ID."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send notifications",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    notify_user_and_record(
        db,
        target_user,
        title=notification.title,
        body=notification.body,
        notification_type="general",
        sent_by_user_id=current_user.id,
        data=notification.data,
    )

    if not target_user.fcm_token:
        return NotificationResponse(
            success=True,
            message=f"Notification saved for {target_user.name} (no push token registered)",
            message_id=None,
        )

    return NotificationResponse(
        success=True,
        message=f"Notification sent to {target_user.name}",
        message_id=None,
    )


@router.post("/all", response_model=NotificationResponse)
async def notify_all(
    notification: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a notification to all users with registered FCM tokens."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can send notifications to all users",
        )

    all_users = db.query(User).all()
    for u in all_users:
        record_notification(
            db,
            user_id=u.id,
            title=notification.title,
            body=notification.body,
            notification_type="general",
            sent_by_user_id=current_user.id,
            data=notification.data,
        )

    tokens = [u.fcm_token for u in all_users if u.fcm_token]

    if not tokens:
        return NotificationResponse(
            success=True,
            message="Notification saved for all users (no push tokens registered)",
            message_id=None,
        )

    if not ensure_firebase_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase is not configured",
        )

    try:
        batch_size = 500
        total_success = 0
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i : i + batch_size]
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data=ensure_string_data(notification.data),
                tokens=batch,
            )
            response = messaging.send_each_for_multicast(message)
            total_success += response.success_count

        return NotificationResponse(
            success=True,
            message=f"Notification saved for all users; push sent to {total_success} devices",
            message_id=None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}",
        ) from e


@router.post("/token", response_model=NotificationResponse)
async def notify_by_token(
    fcm_token: str,
    notification: NotificationRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a notification to a specific FCM token (for testing or direct token sending)."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can send notifications by token",
        )

    response = _send_token_or_http(
        fcm_token,
        notification.title,
        notification.body,
        notification.data,
    )
    return NotificationResponse(
        success=True,
        message="Notification sent successfully",
        message_id=response,
    )
