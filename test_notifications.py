"""Notification diagnostics — run: python test_notifications.py"""
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app.firebase_app import firebase_status
from app.models import User
from app.push_delivery import send_notification_to_token


def main() -> None:
    push = firebase_status()
    print("push_status:", push)

    db = SessionLocal()
    try:
        with_token = db.query(User).filter(User.fcm_token.isnot(None)).all()
        print("users_with_fcm_token:", len(with_token))
        for u in with_token[:10]:
            token = u.fcm_token or ""
            print(f"  id={u.id} name={u.name} role={u.role.value} token_len={len(token)}")

        if not push.get("ready"):
            print("\nCannot send test push — fix Firebase credentials first.")
            return

        if not with_token:
            print("\nNo registered devices — open mobile app on a real phone and log in.")
            return

        user = with_token[0]
        print(f"\nSending test push to user {user.id} ({user.name})...")
        msg_id = send_notification_to_token(
            user.fcm_token,
            "Test notification",
            "If you see this, push notifications are working.",
            {"type": "test"},
        )
        print("send_ok message_id:", msg_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
