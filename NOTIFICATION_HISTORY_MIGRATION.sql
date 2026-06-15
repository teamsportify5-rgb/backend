-- Notification history + forced password change + company email support
-- Run on production database before deploying backend update.

-- PostgreSQL / Supabase:
ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sent_by_user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'general',
    data_json TEXT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notification_log_user_id ON notification_log(user_id);
CREATE INDEX IF NOT EXISTS ix_notification_log_created_at ON notification_log(created_at DESC);

-- MySQL alternative:
-- ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0;
-- (create notification_log with appropriate MySQL types if needed)
