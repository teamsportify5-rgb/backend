from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator
from typing import Optional
from datetime import datetime, date
from app.models import UserRole, OrderStatus, AttendanceStatus
from app.email_validation import assert_company_email


# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
    phone: Optional[str] = None
    daily_rate: Optional[float] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: EmailStr) -> EmailStr:
        assert_company_email(str(v))
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    daily_rate: Optional[float] = None


class UserResponse(UserBase):
    id: int
    must_change_password: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class FCMTokenRequest(BaseModel):
    fcm_token: str


class PasswordResetRequest(BaseModel):
    new_password: Optional[str] = None
    notify: bool = True


class PasswordResetResponse(BaseModel):
    message: str
    new_password: str
    notified: bool


class PasswordResetRequestInput(BaseModel):
    email: EmailStr


class PasswordResetRequestAck(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class NotificationLogResponse(BaseModel):
    id: int
    user_id: int
    sent_by_user_id: Optional[int] = None
    title: str
    body: str
    notification_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Order Schemas
class OrderBase(BaseModel):
    product: str
    quantity: int
    due_date: Optional[date] = None


class OrderCreate(OrderBase):
    customer_id: int


class OrderUpdate(BaseModel):
    product: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[OrderStatus] = None
    due_date: Optional[date] = None


class OrderResponse(OrderBase):
    order_id: int
    customer_id: int
    status: OrderStatus
    created_at: datetime
    due_reminder_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Attendance Schemas
class AttendanceBase(BaseModel):
    date: date
    status: AttendanceStatus


class AttendanceCreate(BaseModel):
    employee_id: int
    date: Optional[date] = None


class AttendanceCheckOut(BaseModel):
    employee_id: int


class AttendanceResponse(AttendanceBase):
    id: int
    employee_id: int
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None

    class Config:
        from_attributes = True


# Payroll Schemas
class PayrollBase(BaseModel):
    days_present: int
    basic_salary: float
    deductions: float
    bonus: float
    net_pay: float
    month: str


class PayrollCreate(BaseModel):
    month: Optional[str] = None  # Format: "YYYY-MM"
    # Optional manual override fields (for admin)
    days_present: Optional[int] = None
    basic_salary: Optional[float] = None
    deductions: Optional[float] = None
    bonus: Optional[float] = None


class PayrollUpdate(BaseModel):
    days_present: Optional[int] = None
    basic_salary: Optional[float] = None
    deductions: Optional[float] = None
    bonus: Optional[float] = None
    # net_pay will be recalculated automatically


class PayrollResponse(PayrollBase):
    payroll_id: int
    employee_id: int
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Inventory Schemas
class InventoryBase(BaseModel):
    item: str
    category: str
    quantity: int = Field(ge=0)
    threshold: int = Field(ge=0)
    unit: str = "pieces"
    unit_price: float = Field(default=0.0, ge=0, description="Cost per unit in Rs")


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    item: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    threshold: Optional[int] = Field(default=None, ge=0)
    unit: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, ge=0)


class InventoryResponse(InventoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def estimated_value(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    class Config:
        from_attributes = True


class InventorySummaryResponse(BaseModel):
    total_items: int
    low_stock_count: int
    total_estimated_value: float


# AI Image Schemas
class AIImageRequest(BaseModel):
    prompt: str


class AIImageResponse(BaseModel):
    image_id: int
    user_id: int
    prompt_text: str
    generated_image_url: str
    created_at: datetime

    class Config:
        from_attributes = True

