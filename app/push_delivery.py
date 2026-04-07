"""Send FCM messages via Firebase Admin; safe no-ops when Firebase is not configured."""
from typing import Any, Dict, Optional

from firebase_admin import messaging

from app.firebase_app import ensure_firebase_initialized
from app.models import User


def ensure_string_data(data: Optional[dict]) -> Dict[str, str]:
    """FCM data payload values must be strings."""
    if not data:
        return {}
    return {k: str(v) for k, v in data.items()}


def send_notification_to_token(
    fcm_token: str, title: str, body: str, data: Optional[dict] = None
) -> str:
    """Send a notification; raises if Firebase is not configured or send fails."""
    if not ensure_firebase_initialized():
        raise RuntimeError("Firebase is not configured (missing credentials)")
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=ensure_string_data(data),
        token=fcm_token,
    )
    return messaging.send(message)


def try_notify_user(
    user: User,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """Send push to user if they have an FCM token. Logs and returns False on failure."""
    if not user or not user.fcm_token:
        return False
    try:
        send_notification_to_token(user.fcm_token, title, body, data)
        return True
    except Exception as e:
        print(f"Push notification failed for user {getattr(user, 'id', '?')}: {e}")
        return False
