-- ============================================================
-- Seed: Create 4 demo users with full org hierarchy
-- Run this AFTER 001 and 002 migrations
-- ============================================================
--
-- Hierarchy:
--   Arjun  (director)   → reports_to: NULL
--   Meera  (manager)    → reports_to: Arjun
--   Priya  (employee)   → reports_to: Meera
--   Rahul  (employee)   → reports_to: Meera
--
-- All passwords: password123
-- ============================================================

-- Create users in auth.users via Supabase's auth admin
-- (You can also create them via the Dashboard or signup page)

-- NOTE: If you prefer, skip this SQL and just register these 4 users
-- through the frontend Register page, then run the UPDATE statements
-- at the bottom to set reports_to.

-- ============================================================
-- OPTION A: Register via frontend, then fix hierarchy
-- ============================================================
-- 1. Register these 4 accounts on http://localhost:5173/auth?mode=register:
--
--    | Name   | Email                | Password    | Role     |
--    |--------|----------------------|-------------|----------|
--    | Arjun  | arjun@ignisia.com    | password123 | Director |
--    | Meera  | meera@ignisia.com    | password123 | Manager  |
--    | Priya  | priya@ignisia.com    | password123 | Employee |
--    | Rahul  | rahul@ignisia.com    | password123 | Employee |
--
-- 2. Then run this in Supabase SQL Editor to set the hierarchy:

-- Set Meera reports to Arjun
UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com')
WHERE email = 'meera@ignisia.com';

-- Set Priya reports to Meera
UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'priya@ignisia.com';

-- Set Rahul reports to Meera
UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'rahul@ignisia.com';
