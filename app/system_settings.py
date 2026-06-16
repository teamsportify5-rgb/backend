"""Singleton system settings (tax rate for payroll, etc.)."""
from sqlalchemy.orm import Session
from app.models import SystemSettings

DEFAULT_TAX_RATE = 10.0


def get_or_create_settings(db: Session) -> SystemSettings:
    settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not settings:
        settings = SystemSettings(id=1, tax_rate=DEFAULT_TAX_RATE)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_tax_rate(db: Session) -> float:
    return get_or_create_settings(db).tax_rate
