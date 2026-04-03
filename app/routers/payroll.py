from typing import List
from datetime import datetime, date
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database import get_db
from app.models import User, Attendance, Payroll, AttendanceStatus, UserRole
from app.schemas import PayrollCreate, PayrollResponse, PayrollUpdate
from app.auth import get_current_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

router = APIRouter()


def _reject_customer_payroll(current_user: User) -> None:
    """Match web app: payroll is only for staff (not customers)."""
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payroll is not available for customer accounts.",
        )


def calculate_days_present(db: Session, employee_id: int, month: str) -> int:
    """Calculate number of days present in a given month"""
    year, month_num = map(int, month.split("-"))
    start_date = date(year, month_num, 1)
    _, last_day = monthrange(year, month_num)
    end_date = date(year, month_num, last_day)

    days_present = (
        db.query(func.count(Attendance.id))
        .filter(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date,
                Attendance.status == AttendanceStatus.PRESENT,
            )
        )
        .scalar()
    )

    return days_present or 0


@router.post("/generate/{employee_id}", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
async def generate_payroll(
    employee_id: int,
    payroll_data: PayrollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only admin, manager, and accountant can generate payroll
    if current_user.role.value not in ["admin", "manager", "accountant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate payroll",
        )

    # Verify employee exists
    employee = db.query(User).filter(User.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    # Use provided month or current month
    if payroll_data.month:
        month = payroll_data.month
    else:
        today = date.today()
        month = f"{today.year}-{today.month:02d}"

    # Check if payroll already exists for this month
    existing_payroll = (
        db.query(Payroll)
        .filter(
            Payroll.employee_id == employee_id,
            Payroll.month == month,
        )
        .first()
    )

    if existing_payroll:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payroll already generated for {month}",
        )

    # Calculate days present (use manual override if provided, otherwise calculate from attendance)
    if payroll_data.days_present is not None:
        days_present = payroll_data.days_present
    else:
        days_present = calculate_days_present(db, employee_id, month)

    # Calculate basic salary
    if payroll_data.basic_salary is not None:
        basic_salary = payroll_data.basic_salary
    else:
        if employee.daily_rate and employee.daily_rate > 0:
            daily_rate = employee.daily_rate
        else:
            daily_rates = {
                "admin": 5000,
                "manager": 4000,
                "accountant": 3000,
                "worker": 2000,
                "customer": 0,
            }
            daily_rate = daily_rates.get(employee.role.value, 2000)
        basic_salary = days_present * daily_rate

    if payroll_data.deductions is not None:
        deductions = payroll_data.deductions
    else:
        deductions = basic_salary * 0.1

    if payroll_data.bonus is not None:
        bonus = payroll_data.bonus
    else:
        bonus = basic_salary * 0.05 if days_present > 25 else 0.0

    net_pay = basic_salary - deductions + bonus

    new_payroll = Payroll(
        employee_id=employee_id,
        days_present=days_present,
        basic_salary=basic_salary,
        deductions=deductions,
        bonus=bonus,
        net_pay=net_pay,
        month=month,
    )
    db.add(new_payroll)
    db.commit()
    db.refresh(new_payroll)
    return new_payroll


# Static path segments MUST be registered before /{employee_id} or FastAPI matches
# "slip", "update", "delete" as employee_id and fails / breaks clients.


@router.get("/slip/{payroll_id}")
async def get_payroll_slip(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _reject_customer_payroll(current_user)

    payroll = db.query(Payroll).filter(Payroll.payroll_id == payroll_id).first()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found",
        )

    if current_user.role.value not in ["admin", "manager", "accountant"] and current_user.id != payroll.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payroll slip",
        )

    employee = db.query(User).filter(User.id == payroll.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee record not found for this payroll",
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1e40af"),
        spaceAfter=30,
        alignment=1,
    )

    story.append(Paragraph("PAYROLL SLIP", title_style))
    story.append(Spacer(1, 0.2 * inch))

    gen_at = payroll.generated_at
    gen_str = gen_at.strftime("%Y-%m-%d %H:%M:%S") if gen_at else "—"

    emp_data = [
        ["Employee Name:", employee.name],
        ["Employee ID:", str(employee.id)],
        ["Email:", employee.email],
        ["Role:", employee.role.value.title()],
        ["Month:", payroll.month],
        ["Generated Date:", gen_str],
    ]

    emp_table = Table(emp_data, colWidths=[2 * inch, 4 * inch])
    emp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ]
        )
    )
    story.append(emp_table)
    story.append(Spacer(1, 0.3 * inch))

    payroll_data = [
        ["Description", "Amount (Rs.)"],
        ["Days Present", str(payroll.days_present)],
        ["Basic Salary", f"{payroll.basic_salary:.2f}"],
        ["Deductions", f"{payroll.deductions:.2f}"],
        ["Bonus", f"{payroll.bonus:.2f}"],
        ["Net Pay", f"{payroll.net_pay:.2f}"],
    ]

    payroll_table = Table(payroll_data, colWidths=[4 * inch, 2 * inch])
    payroll_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dbeafe")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
            ]
        )
    )
    story.append(payroll_table)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payroll_slip_{payroll_id}.pdf"},
    )


@router.put("/update/{payroll_id}", response_model=PayrollResponse)
async def update_payroll(
    payroll_id: int,
    payroll_data: PayrollUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update payroll record. Only admin and accountant can update."""
    if current_user.role.value not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update payroll records",
        )

    payroll = db.query(Payroll).filter(Payroll.payroll_id == payroll_id).first()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found",
        )

    if payroll_data.days_present is not None:
        payroll.days_present = payroll_data.days_present
    if payroll_data.basic_salary is not None:
        payroll.basic_salary = payroll_data.basic_salary
    if payroll_data.deductions is not None:
        payroll.deductions = payroll_data.deductions
    if payroll_data.bonus is not None:
        payroll.bonus = payroll_data.bonus

    payroll.net_pay = payroll.basic_salary - payroll.deductions + payroll.bonus

    db.commit()
    db.refresh(payroll)
    return payroll


@router.delete("/delete/{payroll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payroll(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a payroll record. Only admin can delete."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete payroll records",
        )

    payroll = db.query(Payroll).filter(Payroll.payroll_id == payroll_id).first()
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found",
        )

    db.delete(payroll)
    db.commit()
    return None


@router.get("/", response_model=List[PayrollResponse])
async def get_all_payroll_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all payroll records. Only admin, manager, and accountant can access."""
    _reject_customer_payroll(current_user)

    if current_user.role.value not in ["admin", "manager", "accountant"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view all payroll records",
        )

    payroll_records = (
        db.query(Payroll)
        .order_by(
            Payroll.month.desc(),
            Payroll.employee_id,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return payroll_records


@router.get("/{employee_id}", response_model=List[PayrollResponse])
async def get_payroll_records(
    employee_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _reject_customer_payroll(current_user)

    if current_user.role.value not in ["admin", "manager", "accountant"] and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this employee's payroll",
        )

    payroll_records = (
        db.query(Payroll)
        .filter(Payroll.employee_id == employee_id)
        .offset(skip)
        .limit(limit)
        .order_by(Payroll.month.desc())
        .all()
    )

    return payroll_records
