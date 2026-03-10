from typing import List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Attendance, AttendanceStatus
from app.schemas import AttendanceCreate, AttendanceCheckOut, AttendanceResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/check-in", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    attendance_data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Use current user's ID if not specified or if user is checking themselves in
    employee_id = attendance_data.employee_id if current_user.role.value in ["admin", "manager"] else current_user.id
    
    # Verify employee exists
    employee = db.query(User).filter(User.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check if attendance record already exists for today
    today = attendance_data.date if attendance_data.date else date.today()
    existing_attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == today
    ).first()
    
    if existing_attendance:
        if existing_attendance.check_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already checked in for today"
            )
        existing_attendance.check_in = datetime.utcnow()
        existing_attendance.status = AttendanceStatus.PRESENT
        db.commit()
        db.refresh(existing_attendance)
        return existing_attendance
    
    # Create new attendance record
    check_in_time = datetime.utcnow()
    new_attendance = Attendance(
        employee_id=employee_id,
        check_in=check_in_time,
        date=today,
        status=AttendanceStatus.PRESENT
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    return new_attendance


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    attendance_data: AttendanceCheckOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Use current user's ID if not specified or if user is checking themselves out
    employee_id = attendance_data.employee_id if current_user.role.value in ["admin", "manager"] else current_user.id
    
    today = date.today()
    attendance = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date == today
    ).first()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No check-in record found for today"
        )
    
    if attendance.check_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked out for today"
        )
    
    attendance.check_out = datetime.utcnow()
    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/today", response_model=List[AttendanceResponse])
async def get_today_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    
    # Admin and manager can see all attendance
    # Others can only see their own
    if current_user.role.value in ["admin", "manager"]:
        attendance_records = db.query(Attendance).filter(Attendance.date == today).all()
    else:
        attendance_records = db.query(Attendance).filter(
            Attendance.employee_id == current_user.id,
            Attendance.date == today
        ).all()
    
    return attendance_records


@router.get("/employee/{employee_id}", response_model=List[AttendanceResponse])
async def get_employee_attendance(
    employee_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check permissions
    if current_user.role.value not in ["admin", "manager"] and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this employee's attendance"
        )
    
    attendance_records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id
    ).offset(skip).limit(limit).order_by(Attendance.date.desc()).all()
    
    return attendance_records

