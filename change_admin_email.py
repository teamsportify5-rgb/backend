"""
Change an admin user's email (e.g. admin@factory.com → admin@sportify.com).

JWT login uses email, so sign in again with the new address after running this.

Usage:
    py change_admin_email.py
    py change_admin_email.py --old admin@factory.com --new admin@sportify.com
    py change_admin_email.py --old admin@factory.com --new admin@sportify.com --dry-run
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func

from app.database import SessionLocal
from app.models import User, UserRole
from app.email_validation import assert_company_email

DEFAULT_OLD_EMAIL = "admin@factory.com"
DEFAULT_NEW_EMAIL = "admin@sportify.com"


def change_admin_email(
    old_email: str,
    new_email: str,
    *,
    dry_run: bool = False,
    require_admin_role: bool = True,
) -> bool:
    old_normalized = old_email.strip().lower()
    try:
        new_normalized = assert_company_email(new_email)
    except ValueError as e:
        print(f"❌ Invalid new email: {e}")
        return False

    if old_normalized == new_normalized:
        print("❌ Old and new email are the same.")
        return False

    db = SessionLocal()
    try:
        user = db.query(User).filter(func.lower(User.email) == old_normalized).first()
        if not user:
            print(f"❌ No user found with email: {old_email}")
            return False

        if require_admin_role and user.role != UserRole.ADMIN:
            print(f"❌ User {old_email} is role '{user.role.value}', not admin. Aborting.")
            return False

        conflict = (
            db.query(User)
            .filter(func.lower(User.email) == new_normalized, User.id != user.id)
            .first()
        )
        if conflict:
            print(f"❌ Email already in use by user id {conflict.id} ({conflict.email}).")
            return False

        print("Admin email change")
        print("=" * 50)
        print(f"  User ID:  {user.id}")
        print(f"  Name:     {user.name}")
        print(f"  Role:     {user.role.value}")
        print(f"  Old email: {user.email}")
        print(f"  New email: {new_normalized}")

        if dry_run:
            print("\n(dry-run — no changes written)")
            return True

        user.email = new_normalized
        db.commit()
        db.refresh(user)

        print("\n✅ Email updated successfully.")
        print("   Sign in with the new email. Existing sessions may need a fresh login.")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Change admin email (default: admin@factory.com → admin@sportify.com)"
    )
    parser.add_argument(
        "--old",
        default=DEFAULT_OLD_EMAIL,
        help=f"Current email (default: {DEFAULT_OLD_EMAIL})",
    )
    parser.add_argument(
        "--new",
        default=DEFAULT_NEW_EMAIL,
        help=f"New email (default: {DEFAULT_NEW_EMAIL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without updating the database",
    )
    parser.add_argument(
        "--any-role",
        action="store_true",
        help="Allow changing email for non-admin users matched by --old",
    )
    args = parser.parse_args()

    ok = change_admin_email(
        args.old,
        args.new,
        dry_run=args.dry_run,
        require_admin_role=not args.any_role,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
