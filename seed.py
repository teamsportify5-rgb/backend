"""
Seeder Script - Sportify Management System
Populates the database with initial sample data.

Usage:
    py seed.py           # Seed all data (skip existing)
    py seed.py --reset   # Clear all data and re-seed (DANGER: deletes everything)
"""

import sys
import os
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, UserRole, Order, OrderStatus, Attendance, AttendanceStatus, Inventory, Payroll, AIImageLog
from app.auth import get_password_hash

# Default password for all seeded users (change after first login)
DEFAULT_PASSWORD = "password123"


def create_users(db):
    """Create sample users for each role."""
    users_data = [
        {"name": "Admin User", "email": "admin@sportify.com", "role": UserRole.ADMIN, "phone": "+1234567890"},
        {"name": "Manager John", "email": "manager@sportify.com", "role": UserRole.MANAGER, "phone": "+1234567891"},
        {"name": "Accountant Mary", "email": "accountant@sportify.com", "role": UserRole.ACCOUNTANT, "phone": "+1234567892", "daily_rate": 150.0},
        {"name": "Worker Bob", "email": "worker@sportify.com", "role": UserRole.WORKER, "phone": "+1234567893", "daily_rate": 80.0},
        {"name": "Worker Alice", "email": "worker2@sportify.com", "role": UserRole.WORKER, "phone": "+1234567894", "daily_rate": 75.0},
        {"name": "Customer Smith", "email": "customer@sportify.com", "role": UserRole.CUSTOMER, "phone": "+1234567895"},
        {"name": "Customer Jane", "email": "customer2@sportify.com", "role": UserRole.CUSTOMER, "phone": "+1234567896"},
    ]

    created = []
    for u in users_data:
        if db.query(User).filter(User.email == u["email"]).first():
            continue
        user = User(
            name=u["name"],
            email=u["email"],
            password_hash=get_password_hash(DEFAULT_PASSWORD),
            role=u["role"],
            phone=u.get("phone"),
            daily_rate=u.get("daily_rate"),
        )
        db.add(user)
        created.append(u["email"])

    if created:
        db.commit()
        print(f"  ✓ Users: {len(created)} created ({', '.join(created)})")
    else:
        print("  - Users: all exist, skipped")


def create_inventory(db):
    """Create sample inventory items."""
    items = [
        {"item": "Widget A", "category": "Electronics", "quantity": 100, "threshold": 10, "unit": "pieces"},
        {"item": "Widget B", "category": "Electronics", "quantity": 50, "threshold": 5, "unit": "pieces"},
        {"item": "Raw Material X", "category": "Raw Materials", "quantity": 500, "threshold": 100, "unit": "kg"},
        {"item": "Raw Material Y", "category": "Raw Materials", "quantity": 200, "threshold": 50, "unit": "kg"},
        {"item": "Component Z", "category": "Components", "quantity": 75, "threshold": 20, "unit": "pieces"},
    ]

    created = []
    for i in items:
        if db.query(Inventory).filter(Inventory.item == i["item"]).first():
            continue
        inv = Inventory(**i)
        db.add(inv)
        created.append(i["item"])

    if created:
        db.commit()
        print(f"  ✓ Inventory: {len(created)} items created")
    else:
        print("  - Inventory: all exist, skipped")


def create_orders(db):
    """Create sample orders (requires customers)."""
    customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()
    if not customers:
        print("  - Orders: no customers, skipped")
        return

    products = ["Widget A", "Widget B", "Component Z"]
    statuses = [OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED, OrderStatus.DELAYED]

    created = 0
    for i, cust in enumerate(customers[:2]):
        for j in range(3):
            product = products[j % len(products)]
            existing = db.query(Order).filter(
                Order.customer_id == cust.id,
                Order.product == product,
            ).first()
            if existing:
                continue

            order = Order(
                customer_id=cust.id,
                product=product,
                quantity=(j + 1) * 5,
                status=statuses[(i + j) % len(statuses)],
                due_date=date.today() + timedelta(days=7 + j),
            )
            db.add(order)
            created += 1

    if created:
        db.commit()
        print(f"  ✓ Orders: {created} created")
    else:
        print("  - Orders: all exist, skipped")


def create_attendance(db):
    """Create sample attendance (requires workers)."""
    workers = db.query(User).filter(User.role == UserRole.WORKER).all()
    if not workers:
        print("  - Attendance: no workers, skipped")
        return

    today = date.today()
    created = 0
    for w in workers:
        for days_ago in range(5):
            d = today - timedelta(days=days_ago)
            if db.query(Attendance).filter(
                Attendance.employee_id == w.id,
                Attendance.date == d,
            ).first():
                continue
            att = Attendance(
                employee_id=w.id,
                date=d,
                check_in=datetime.now() - timedelta(days=days_ago, hours=8),
                check_out=datetime.now() - timedelta(days=days_ago, hours=1),
                status=AttendanceStatus.PRESENT,
            )
            db.add(att)
            created += 1

    if created:
        db.commit()
        print(f"  ✓ Attendance: {created} records created")
    else:
        print("  - Attendance: all exist, skipped")


def create_payroll(db):
    """Create sample payroll (requires workers)."""
    workers = db.query(User).filter(
        User.role.in_([UserRole.WORKER, UserRole.ACCOUNTANT, UserRole.MANAGER])  # type: ignore
    ).all()
    if not workers:
        print("  - Payroll: no employees, skipped")
        return

    month = date.today().strftime("%Y-%m")
    created = 0
    for w in workers:
        if db.query(Payroll).filter(
            Payroll.employee_id == w.id,
            Payroll.month == month,
        ).first():
            continue
        days = 20
        rate = w.daily_rate or 100.0
        basic = days * rate
        deductions = basic * 0.05
        bonus = 50.0
        net = basic - deductions + bonus
        pr = Payroll(
            employee_id=w.id,
            days_present=days,
            basic_salary=basic,
            deductions=deductions,
            bonus=bonus,
            net_pay=net,
            month=month,
        )
        db.add(pr)
        created += 1

    if created:
        db.commit()
        print(f"  ✓ Payroll: {created} records created for {month}")
    else:
        print("  - Payroll: all exist, skipped")


def reset_all(db):
    """Delete all data (order matters for foreign keys)."""
    db.query(Payroll).delete()
    db.query(Attendance).delete()
    db.query(Order).delete()
    db.query(AIImageLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.commit()
    print("  ✓ All data cleared")


def main():
    reset = "--reset" in sys.argv

    print("\n🌱 Sportify Management System - Seeder")
    print("=" * 50)

    db = SessionLocal()
    try:
        if reset:
            print("\n⚠️  RESET MODE: Deleting all existing data...")
            reset_all(db)

        print("\nSeeding...")
        create_users(db)
        create_inventory(db)
        create_orders(db)
        create_attendance(db)
        create_payroll(db)

        print("\n" + "=" * 50)
        print("✅ Seeding complete!")
        print("\n📋 Default credentials (password for all): " + DEFAULT_PASSWORD)
        print("   admin@sportify.com      - Admin")
        print("   manager@sportify.com    - Manager")
        print("   accountant@sportify.com - Accountant")
        print("   worker@sportify.com     - Worker")
        print("   customer@sportify.com   - Customer")
        print("\n⚠️  Change passwords after first login!\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
