from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Date, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ACCOUNTANT = "accountant"
    WORKER = "worker"
    CUSTOMER = "customer"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.WORKER)
    phone = Column(String(20), nullable=True)
    fcm_token = Column(String(500), nullable=True)  # Firebase Cloud Messaging token for push notifications
    # Salary settings (can be set by admin)
    daily_rate = Column(Float, nullable=True)  # Daily salary rate
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer")
    attendance_records = relationship("Attendance", back_populates="employee")
    payroll_records = relationship("Payroll", back_populates="employee")
    ai_image_logs = relationship("AIImageLog", back_populates="user")
    notifications_received = relationship(
        "NotificationLog",
        back_populates="recipient",
        foreign_keys="NotificationLog.user_id",
    )
    tasks_assigned = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assigned_to_id",
    )
    tasks_created = relationship(
        "Task",
        back_populates="assigner",
        foreign_keys="Task.assigned_by_id",
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sent_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False, default="general")
    data_json = Column(Text, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", foreign_keys=[user_id], back_populates="notifications_received")
    sender = relationship("User", foreign_keys=[sent_by_user_id])


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    due_date = Column(Date, nullable=True)
    due_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    customer = relationship("User", back_populates="orders")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    date = Column(Date, nullable=False, index=True)

    # Relationships
    employee = relationship("User", back_populates="attendance_records")


class Payroll(Base):
    __tablename__ = "payroll"

    payroll_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    days_present = Column(Integer, nullable=False, default=0)
    basic_salary = Column(Float, nullable=False, default=0.0)
    deductions = Column(Float, nullable=False, default=0.0)
    bonus = Column(Float, nullable=False, default=0.0)
    net_pay = Column(Float, nullable=False, default=0.0)
    month = Column(String(20), nullable=False)  # Format: "YYYY-MM"
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    employee = relationship("User", back_populates="payroll_records")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String(200), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    threshold = Column(Integer, nullable=False, default=0)
    unit = Column(String(50), nullable=False, default="pieces")
    unit_price = Column(Float, nullable=False, default=0.0)  # Cost per unit (Rs) for stock valuation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIImageLog(Base):
    __tablename__ = "ai_image_log"

    image_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    generated_image_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="ai_image_logs")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    assignee = relationship("User", foreign_keys=[assigned_to_id], back_populates="tasks_assigned")
    assigner = relationship("User", foreign_keys=[assigned_by_id], back_populates="tasks_created")


class SystemSettings(Base):
    """Singleton row (id=1) for system-wide configuration."""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    tax_rate = Column(Float, nullable=False, default=10.0)  # Payroll tax deduction %
