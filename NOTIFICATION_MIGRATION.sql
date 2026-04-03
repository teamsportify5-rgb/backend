-- Run this to add fcm_token column for push notifications
-- Supabase/PostgreSQL:
ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(500) NULL;
-- MySQL (if column doesn't exist):
-- ALTER TABLE users ADD COLUMN fcm_token VARCHAR(500) NULL;
