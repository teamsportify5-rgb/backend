-- One-time reminder per order when due date enters the 3-day window (see /internal/cron/order-due-reminders)
-- PostgreSQL / Supabase:
ALTER TABLE orders ADD COLUMN IF NOT EXISTS due_reminder_sent_at TIMESTAMPTZ NULL;
-- MySQL 8+:
-- ALTER TABLE orders ADD COLUMN due_reminder_sent_at DATETIME NULL;
