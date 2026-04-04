-- ============================================================
-- Seed data: Demo organization matching the current org_model.py
-- ============================================================
-- NOTE: In production, users are created via Supabase Auth signup.
-- This seed creates the org so the demo team can be onboarded.
-- ============================================================

INSERT INTO organizations (id, name, slug)
VALUES ('a0000000-0000-0000-0000-000000000001', 'Ignisia Demo', 'ignisia-demo')
ON CONFLICT (slug) DO NOTHING;

-- The four demo users will be created when they sign up via Auth.
-- Their signup payload should include:
--   raw_user_meta_data: {
--     "org_id": "a0000000-0000-0000-0000-000000000001",
--     "full_name": "Arjun",
--     "role": "director"
--   }
--
-- Org hierarchy (set reports_to after all users exist):
--   Arjun  (director)  → reports_to: NULL
--   Meera  (manager)   → reports_to: Arjun
--   Priya  (employee)  → reports_to: Meera
--   Rahul  (employee)  → reports_to: Meera
