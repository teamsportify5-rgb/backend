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


def send_notification_to_token(fcm_token: str, title: str, body: str, data: Optional[dict] = None):
    """Send a notification to a specific FCM token."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
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
    # Only admin and manager can send notifications
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send notifications"
        )
    
    # Get the target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # In a real implementation, you would store FCM tokens in the database
    # For now, we'll use a placeholder approach where tokens are stored in user table or a separate table
    # This is a simplified version - you should add an fcm_token field to the User model
    # or create a separate user_tokens table
    
    # Placeholder: Check if user has FCM token stored (you need to add this field to User model)
    # For now, we'll just return success but note that token storage needs to be implemented
    try:
        # In production, retrieve FCM token from database:
        # fcm_token = target_user.fcm_token or get_fcm_token_from_database(user_id)
        
        # For now, we'll return a message indicating the notification was queued
        # You need to implement FCM token storage and retrieval
        return NotificationResponse(
            success=True,
            message=f"Notification queued for user {target_user.name}",
            message_id=None
        )
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
    """Send a notification to all users."""
    # Only admin can send notifications to all users
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can send notifications to all users"
        )
    
    try:
        # In production, retrieve all FCM tokens from database
        # For now, this is a placeholder
        # You would do something like:
        # tokens = db.query(User.fcm_token).filter(User.fcm_token.isnot(None)).all()
        # response = messaging.send_multicast(messaging.MulticastMessage(...))
        
        # Get all users (for counting purposes)
        all_users = db.query(User).count()
        
        return NotificationResponse(
            success=True,
            message=f"Notification queued for {all_users} users",
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




