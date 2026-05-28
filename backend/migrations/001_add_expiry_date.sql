-- Adds expiry_date column to inventory table needed by the frontend and chef priority logic.
ALTER TABLE public.inventory ADD COLUMN IF NOT EXISTS expiry_date DATE;

-- Also adds user_id column to receipts table (referenced by receipts.py but missing from schema).
ALTER TABLE public.receipts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
