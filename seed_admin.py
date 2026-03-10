"""
Admin Seeder Script
Creates the initial admin user for the Sportify Management System.

Usage:
    python seed_admin.py
    OR
    py seed_admin.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, UserRole
from app.auth import get_password_hash

def create_admin_user():
    """Create the default admin user if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@sportify.com").first()
        
        if existing_admin:
            print("❌ Admin user already exists!")
            print(f"   Email: {existing_admin.email}")
            print(f"   Name: {existing_admin.name}")
            print("\n💡 To create a new admin, use a different email or delete the existing admin first.")
            return False
        
        # Create admin user
        admin_user = User(
            name="Admin User",
            email="admin@sportify.com",
            password_hash=get_password_hash("admin123"),  # Default password - CHANGE THIS!
            role=UserRole.ADMIN,
            phone="+1234567890"
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print("\n📋 Admin Credentials:")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: admin123")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")
        print("\n🔐 To change password, login and update it in User Management.")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        return False
    finally:
        db.close()

def create_custom_admin(name: str, email: str, password: str, phone: str = None):
    """Create a custom admin user."""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return False
        
        # Create admin user
        admin_user = User(
            name=name,
            email=email,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            phone=phone
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user '{name}' created successfully!")
        print(f"   Email: {email}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create admin user for Sportify Management System")
    parser.add_argument("--name", type=str, help="Admin name (default: Admin User)")
    parser.add_argument("--email", type=str, help="Admin email (default: admin@sportify.com)")
    parser.add_argument("--password", type=str, help="Admin password (default: admin123)")
    parser.add_argument("--phone", type=str, help="Admin phone number (optional)")
    
    args = parser.parse_args()
    
    if args.name and args.email and args.password:
        # Create custom admin
        create_custom_admin(
            name=args.name,
            email=args.email,
            password=args.password,
            phone=args.phone
        )
    else:
        # Create default admin
        print("🌱 Seeding default admin user...")
        print("=" * 50)
        create_admin_user()
        print("=" * 50)



