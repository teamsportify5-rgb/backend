-- Add unit_price column for real inventory valuation (quantity × unit_price)
-- Run on your production database before deploying the backend update.

-- PostgreSQL / Supabase:
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS unit_price DOUBLE PRECISION NOT NULL DEFAULT 0;

-- MySQL (if not using PostgreSQL):
-- ALTER TABLE inventory ADD COLUMN unit_price DOUBLE NOT NULL DEFAULT 0;
