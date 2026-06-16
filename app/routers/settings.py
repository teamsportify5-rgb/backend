from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import SystemSettingsResponse, SystemSettingsUpdate
from app.auth import get_current_user
from app.system_settings import get_or_create_settings

router = APIRouter()


def _require_admin(current_user: User) -> None:
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can change system settings",
        )


def _require_payroll_staff(current_user: User) -> None:
    if current_user.role.value not in ("admin", "manager", "accountant"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view system settings",
        )


@router.get("/", response_model=SystemSettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read system settings (tax rate). Available to payroll staff."""
    _require_payroll_staff(current_user)
    settings = get_or_create_settings(db)
    return settings


@router.patch("/", response_model=SystemSettingsResponse)
async def update_settings(
    body: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update system settings. Admin only."""
    _require_admin(current_user)
    settings = get_or_create_settings(db)
    if body.tax_rate is not None:
        settings.tax_rate = body.tax_rate
    db.commit()
    db.refresh(settings)
    return settings
