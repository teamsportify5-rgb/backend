from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from app.database import get_db
from app.models import User, UserRole, Order, Attendance, Payroll, AIImageLog, NotificationLog, Task
from app.schemas import (
    UserCreate, UserUpdate, UserResponse, Token, LoginRequest, FCMTokenRequest,
    PasswordResetRequest, PasswordResetResponse, PasswordResetRequestInput,
    PasswordResetRequestAck, ChangePasswordRequest, ChangeEmailRequest, ChangeEmailResponse,
)
from app.notification_history import notify_user_and_record, record_notification
from app.auth import (
    get_password_hash,
    verify_password,
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import secrets
import string

router = APIRouter()


def _generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _delete_user_dependencies(db: Session, user_id: int) -> None:
    """Remove rows that reference this user so the user row can be deleted."""
    db.query(Payroll).filter(Payroll.employee_id == user_id).delete(synchronize_session=False)
    db.query(Attendance).filter(Attendance.employee_id == user_id).delete(synchronize_session=False)
    db.query(Order).filter(Order.customer_id == user_id).delete(synchronize_session=False)
    db.query(AIImageLog).filter(AIImageLog.user_id == user_id).delete(synchronize_session=False)
    db.query(NotificationLog).filter(NotificationLog.user_id == user_id).delete(synchronize_session=False)
    db.query(NotificationLog).filter(NotificationLog.sent_by_user_id == user_id).update(
        {NotificationLog.sent_by_user_id: None},
        synchronize_session=False,
    )
    db.query(Task).filter(Task.assigned_to_id == user_id).delete(synchronize_session=False)
    db.query(Task).filter(Task.assigned_by_id == user_id).update(
        {Task.assigned_by_id: None},
        synchronize_session=False,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new user. Only admin can create users."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create users. Use User Management page."
        )
    
    if user_data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create admin users",
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=str(user_data.email).lower(),
        password_hash=hashed_password,
        role=user_data.role,
        phone=user_data.phone,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def _token_response_for_user(user: User) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Mobile/web: JSON `{"email","password"}`.
    Swagger OAuth2 Authorize: form `username` (your email) + `password`.
    """
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()

    if content_type == "application/json":
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON body",
            )
        try:
            login_data = LoginRequest(**body)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Expected JSON: {"email":"you@example.com","password":"..."}',
            )
        user = authenticate_user(db, str(login_data.email), login_data.password)
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Send JSON {email,password} or form fields username (email) and password",
            )
        user = authenticate_user(db, str(username), str(password))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response_for_user(user)


@router.post("/request-password-reset", response_model=PasswordResetRequestAck)
async def request_password_reset(
    body: PasswordResetRequestInput,
    db: Session = Depends(get_db),
):
    """
    Public endpoint: user requests a password reset. Notifies all admins via push (free).
    Always returns the same message whether or not the email exists (privacy).
    """
    email = str(body.email).strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()

    if user:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        for admin in admins:
            notify_user_and_record(
                db,
                admin,
                title="Password reset requested",
                body=f"{user.name} ({user.email}) requested a password reset. Open User Management to reset their password.",
                notification_type="password_reset_request",
                data={"type": "password_reset_request", "user_id": str(user.id), "email": user.email},
            )

    return PasswordResetRequestAck(
        message=(
            "Your request has been submitted. If an account exists for this email, "
            "an administrator will be notified and will reset your password."
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User changes their own password (required after admin reset)."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-email", response_model=ChangeEmailResponse)
async def change_email(
    body: ChangeEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User changes their own email (new address must be @sportify.com). Returns a new JWT."""
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect",
        )

    new_email = str(body.new_email).strip().lower()
    if new_email == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email is the same as your current email",
        )

    existing = db.query(User).filter(func.lower(User.email) == new_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    current_user.email = new_email
    db.commit()
    db.refresh(current_user)

    token = _token_response_for_user(current_user)
    return ChangeEmailResponse(
        message="Email updated successfully. Use your new email next time you sign in.",
        access_token=token.access_token,
        token_type=token.token_type,
        user=current_user,
    )


@router.post("/register-fcm-token")
async def register_fcm_token(
    data: FCMTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register FCM token for push notifications. Call from mobile app after login."""
    current_user.fcm_token = data.fcm_token
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raw = str(getattr(e, "orig", e)).lower()
        if "fcm_token" in raw or "no such column" in raw:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Database is missing the fcm_token column. "
                    "Run backend/NOTIFICATION_MIGRATION.sql on your database, then redeploy if needed."
                ),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save push token.",
        ) from e
    return {"message": "FCM token registered"}


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    role: Optional[str] = Query(None, description="Filter by role (e.g., 'customer')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users. Admin, manager, and accountant can list users (accountant: payroll)."""
    if current_user.role.value not in ["admin", "manager", "accountant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view users"
        )
    
    query = db.query(User)
    if role:
        # Filter by role enum value
        from app.models import UserRole
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}. Valid roles are: {[r.value for r in UserRole]}"
            )
    
    users = query.all()
    return users


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user. Only admin can update users."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields if provided
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = str(user_data.email).lower()
    if user_data.role is not None:
        if user.role == UserRole.ADMIN:
            if user_data.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change the admin role",
                )
        elif user_data.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign admin role",
            )
        else:
            user.role = user_data.role
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.daily_rate is not None:
        # Allow setting to None/empty to clear the rate
        user.daily_rate = user_data.daily_rate if user_data.daily_rate > 0 else None
    
    # Update password if provided
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)
        user.must_change_password = True
    
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: int,
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin resets a user's password and optionally notifies them via push (free, no email service)."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can reset passwords",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_password = (body.new_password or "").strip() or _generate_temp_password()
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = True
    db.commit()

    notified = False
    if body.notify:
        notified = notify_user_and_record(
            db,
            user,
            title="Password reset",
            body=(
                "Your Sportify password was reset by an administrator. "
                "Sign in with the temporary password they provide, then you will be asked to set a new password."
            ),
            notification_type="password_reset",
            sent_by_user_id=current_user.id,
            data={"type": "password_reset", "must_change_password": "true"},
        )

    return PasswordResetResponse(
        message=(
            f"Password reset for {user.name}. "
            + ("User notified via push notification." if notified else "Push notification not sent (user may not have the mobile app registered).")
        ),
        new_password=new_password,
        notified=notified,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user. Only admin can delete users."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete users"
        )
    
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be deleted",
        )

    try:
        _delete_user_dependencies(db, user_id)
        db.delete(user)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not delete user because related records still exist. Try again or contact support.",
        ) from exc

    return None
