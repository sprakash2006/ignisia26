

INSERT INTO organizations (id, name, slug)
VALUES ('a0000000-0000-0000-0000-000000000001', 'Ignisia Demo', 'ignisia-demo')
ON CONFLICT (slug) DO NOTHING;

