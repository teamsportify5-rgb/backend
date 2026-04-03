from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.auth import get_current_user
import firebase_admin
from firebase_admin import credentials, messaging
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Initialize Firebase Admin SDK
try:
    # Try to initialize with service account JSON file path
    firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if firebase_credentials_path and os.path.exists(firebase_credentials_path):
        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    else:
        # Try to initialize with JSON content from environment variable
        firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if firebase_credentials_json:
            import json
            cred_info = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_info)
            firebase_admin.initialize_app(cred)
        else:
            # Default app might already be initialized
            try:
                firebase_admin.get_app()
            except ValueError:
                # If not initialized and no credentials provided, we'll handle errors in endpoints
                pass
except Exception as e:
    print(f"Warning: Firebase Admin SDK initialization failed: {e}")
    print("Notifications will not work until Firebase credentials are configured.")


class NotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[dict] = None


class NotificationResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None


def _ensure_string_data(data: Optional[dict]) -> dict:
    """FCM data payload values must be strings."""
    if not data:
        return {}
    return {k: str(v) for k, v in data.items()}


def send_notification_to_token(fcm_token: str, title: str, body: str, data: Optional[dict] = None):
    """Send a notification to a specific FCM token."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=_ensure_string_data(data),
            token=fcm_token,
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.post("/user/{user_id}", response_model=NotificationResponse)
async def notify_user(
    user_id: int,
    notification: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a notification to a specific user by user ID."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send notifications"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not target_user.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {target_user.name} has not registered for push notifications"
        )
    
    try:
        msg_id = send_notification_to_token(
            fcm_token=target_user.fcm_token,
            title=notification.title,
            body=notification.body,
            data=notification.data
        )
        return NotificationResponse(
            success=True,
            message=f"Notification sent to {target_user.name}",
            message_id=msg_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.post("/all", response_model=NotificationResponse)
async def notify_all(
    notification: NotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a notification to all users with registered FCM tokens."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can send notifications to all users"
        )
    
    tokens = [u.fcm_token for u in db.query(User).filter(User.fcm_token.is_not(None)).all()]
    
    if not tokens:
        return NotificationResponse(
            success=True,
            message="No users have registered for push notifications",
            message_id=None
        )
    
    try:
        # FCM multicast limit is 500 tokens per request
        batch_size = 500
        total_success = 0
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i + batch_size]
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data=_ensure_string_data(notification.data),
                tokens=batch,
            )
            response = messaging.send_multicast(message)
            total_success += response.success_count
        
        return NotificationResponse(
            success=True,
            message=f"Notification sent to {total_success} users",
            message_id=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}"
        )


@router.post("/token", response_model=NotificationResponse)
async def notify_by_token(
    fcm_token: str,
    notification: NotificationRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a notification to a specific FCM token (for testing or direct token sending)."""
    # Only admin can send notifications by token
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can send notifications by token"
        )
    
    try:
        response = send_notification_to_token(
            fcm_token=fcm_token,
            title=notification.title,
            body=notification.body,
            data=notification.data
        )
        return NotificationResponse(
            success=True,
            message="Notification sent successfully",
            message_id=response
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )




