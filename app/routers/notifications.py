from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from firebase_admin import messaging

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.firebase_app import ensure_firebase_initialized
from app.push_delivery import ensure_string_data, send_notification_to_token

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

    if not target_user.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {target_user.name} has not registered for push notifications",
        )

    msg_id = _send_token_or_http(
        target_user.fcm_token,
        notification.title,
        notification.body,
        notification.data,
    )
    return NotificationResponse(
        success=True,
        message=f"Notification sent to {target_user.name}",
        message_id=msg_id,
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

    tokens = [u.fcm_token for u in db.query(User).filter(User.fcm_token.is_not(None)).all()]

    if not tokens:
        return NotificationResponse(
            success=True,
            message="No users have registered for push notifications",
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
            response = messaging.send_multicast(message)
            total_success += response.success_count

        return NotificationResponse(
            success=True,
            message=f"Notification sent to {total_success} users",
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
