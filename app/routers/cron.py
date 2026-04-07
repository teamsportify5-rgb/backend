"""
Scheduled jobs (e.g. Vercel Cron). Secured with CRON_SECRET Bearer token when set.
See vercel.json for schedule.
"""
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderStatus, User
from app.push_delivery import try_notify_user

router = APIRouter(prefix="/internal/cron", tags=["Cron"])

# Notify assignee once per order when due date is within this many days (inclusive)
DUE_REMINDER_DAYS = 3


def _verify_cron_request(request: Request) -> None:
    secret = os.getenv("CRON_SECRET")
    if os.getenv("VERCEL") and not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET must be set on Vercel for cron endpoints",
        )
    if not secret:
        return
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {secret}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.get("/order-due-reminders")
def run_order_due_reminders(request: Request, db: Session = Depends(get_db)):
    """
    Find orders due within the next DUE_REMINDER_DAYS days (not completed),
    where we have not sent a due reminder yet; notify assignee (customer_id user).
    Vercel Cron calls this route daily (GET).
    """
    _verify_cron_request(request)

    today = date.today()
    window_end = today + timedelta(days=DUE_REMINDER_DAYS)

    orders = (
        db.query(Order)
        .filter(
            Order.due_date.isnot(None),
            Order.due_date >= today,
            Order.due_date <= window_end,
            Order.status != OrderStatus.COMPLETED,
            Order.due_reminder_sent_at.is_(None),
        )
        .all()
    )

    sent = 0
    now = datetime.now(timezone.utc)
    for order in orders:
        assignee = db.query(User).filter(User.id == order.customer_id).first()
        if not assignee:
            continue
        days_left = (order.due_date - today).days
        body = f"{order.product} is due on {order.due_date} ({days_left} day(s) left)."
        if try_notify_user(
            assignee,
            "Order due soon",
            body,
            {
                "type": "order_due_soon",
                "order_id": str(order.order_id),
                "due_date": str(order.due_date),
            },
        ):
            order.due_reminder_sent_at = now
            sent += 1

    if sent:
        db.commit()

    return {
        "ok": True,
        "checked": len(orders),
        "notifications_sent": sent,
        "window_days": DUE_REMINDER_DAYS,
    }
