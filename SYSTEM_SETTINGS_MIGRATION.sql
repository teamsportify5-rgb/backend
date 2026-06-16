-- Run on production DB before deploying tax-rate payroll feature.
-- Default 10% matches previous hardcoded payroll deduction rate.

CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY,
    tax_rate DOUBLE PRECISION NOT NULL DEFAULT 10.0
);

INSERT INTO system_settings (id, tax_rate)
VALUES (1, 10.0)
ON CONFLICT (id) DO NOTHING;
