

UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com')
WHERE email = 'meera@ignisia.com';

UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'priya@ignisia.com';

UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'rahul@ignisia.com';


INSERT INTO documents (id, org_id, owner_id, filename, file_type, file_size_bytes, visibility, source_type, chunk_count, status)
VALUES
  
  (
    'ddd00000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Company_Policy_Handbook_2025.pdf',
    'pdf',
    2458000,
    'shared',
    'upload',
    47,
    'ready'
  ),
  (
    'ddd00000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Employee_Benefits_Summary.docx',
    'docx',
    384000,
    'shared',
    'upload',
    18,
    'ready'
  ),
  (
    'ddd00000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Q1_2025_Revenue_Report.xlsx',
    'xlsx',
    712000,
    'shared',
    'upload',
    32,
    'ready'
  ),
  (
    'ddd00000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Product_Roadmap_H1_2025.pdf',
    'pdf',
    1890000,
    'shared',
    'upload',
    25,
    'ready'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000005',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'priya@ignisia.com'),
    'Priya_Performance_Review_Q4.pdf',
    'pdf',
    156000,
    'private',
    'upload',
    8,
    'ready'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000006',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'rahul@ignisia.com'),
    'Rahul_Expense_Report_March.xlsx',
    'xlsx',
    89000,
    'private',
    'upload',
    5,
    'ready'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000007',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'meera@ignisia.com'),
    'Team_Budget_Allocation_2025.xlsx',
    'xlsx',
    245000,
    'private',
    'upload',
    12,
    'ready'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000008',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'Email_Board_Meeting_Notes_2025-03-15.eml',
    'eml',
    34000,
    'private',
    'email',
    6,
    'ready'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000009',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Annual_Report_2024_Draft.pdf',
    'pdf',
    5200000,
    'shared',
    'upload',
    0,
    'processing'
  ),
  
  (
    'ddd00000-0000-0000-0000-000000000010',
    'a0000000-0000-0000-0000-000000000001',
    NULL,
    'Corrupted_File.pdf',
    'pdf',
    1200,
    'shared',
    'upload',
    0,
    'failed'
  );


INSERT INTO conversations (id, org_id, user_id, title, created_at)
VALUES
  (
    'ccc00000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'Q1 Revenue Analysis',
    now() - interval '2 hours'
  ),
  (
    'ccc00000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'Company Policy Questions',
    now() - interval '1 day'
  ),
  (
    'ccc00000-0000-0000-0000-000000000003',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'meera@ignisia.com'),
    'Team Budget Review',
    now() - interval '3 hours'
  ),
  (
    'ccc00000-0000-0000-0000-000000000004',
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'priya@ignisia.com'),
    'Benefits Inquiry',
    now() - interval '5 hours'
  );


INSERT INTO messages (conversation_id, role, content, sources, analysis, created_at)
VALUES
  
  (
    'ccc00000-0000-0000-0000-000000000001',
    'user',
    'What was our total revenue in Q1 2025?',
    '[]'::jsonb,
    '{}'::jsonb,
    now() - interval '2 hours'
  ),
  (
    'ccc00000-0000-0000-0000-000000000001',
    'assistant',
    E'** Final Answer**\nThe total revenue for Q1 2025 was ₹4.82 Crores, a 23% increase over Q1 2024.\n\n** Data Quality Notes**\nNo data quality issues detected.\n\n** Source References**\n- Q1_2025_Revenue_Report.xlsx, Page 1, Row 12\n\n** Reasoning**\nThe revenue figure was found directly in the quarterly report summary sheet.',
    '[{"document": "Q1_2025_Revenue_Report.xlsx", "page": 1, "line": 12, "similarity": 0.9234}]'::jsonb,
    '{"duplicates": [], "conflicts": [], "unique_sources": ["Q1_2025_Revenue_Report.xlsx"]}'::jsonb,
    now() - interval '1 hour 59 minutes'
  ),
  (
    'ccc00000-0000-0000-0000-000000000001',
    'user',
    'How does that compare to the target?',
    '[]'::jsonb,
    '{}'::jsonb,
    now() - interval '1 hour 55 minutes'
  ),
  (
    'ccc00000-0000-0000-0000-000000000001',
    'assistant',
    E'** Final Answer**\nThe Q1 2025 target was ₹4.5 Crores. Actual revenue of ₹4.82 Crores exceeded the target by 7.1%.\n\n** Data Quality Notes**\nNo data quality issues detected.\n\n** Source References**\n- Q1_2025_Revenue_Report.xlsx, Page 1, Row 12 (actual)\n- Product_Roadmap_H1_2025.pdf, Page 3, Section: Revenue Targets (target)\n\n** Reasoning**\nActual revenue from the Q1 report was compared against the target defined in the H1 roadmap.',
    '[{"document": "Q1_2025_Revenue_Report.xlsx", "page": 1, "line": 12, "similarity": 0.9234}, {"document": "Product_Roadmap_H1_2025.pdf", "page": 3, "line": 1, "similarity": 0.8712}]'::jsonb,
    '{"duplicates": [], "conflicts": [], "unique_sources": ["Q1_2025_Revenue_Report.xlsx", "Product_Roadmap_H1_2025.pdf"]}'::jsonb,
    now() - interval '1 hour 54 minutes'
  ),

  
  (
    'ccc00000-0000-0000-0000-000000000002',
    'user',
    'What is our remote work policy?',
    '[]'::jsonb,
    '{}'::jsonb,
    now() - interval '1 day'
  ),
  (
    'ccc00000-0000-0000-0000-000000000002',
    'assistant',
    E'** Final Answer**\nEmployees may work remotely up to 3 days per week with manager approval. Full-time remote requires director-level approval and a signed remote work agreement.\n\n** Data Quality Notes**\nNo data quality issues detected.\n\n** Source References**\n- Company_Policy_Handbook_2025.pdf, Page 14, Section: Remote Work\n\n** Reasoning**\nThe policy was found in the handbook under the Remote Work section.',
    '[{"document": "Company_Policy_Handbook_2025.pdf", "page": 14, "line": 1, "similarity": 0.9456}]'::jsonb,
    '{"duplicates": [], "conflicts": [], "unique_sources": ["Company_Policy_Handbook_2025.pdf"]}'::jsonb,
    now() - interval '23 hours 59 minutes'
  ),

  
  (
    'ccc00000-0000-0000-0000-000000000003',
    'user',
    'What is the engineering team budget for Q2?',
    '[]'::jsonb,
    '{}'::jsonb,
    now() - interval '3 hours'
  ),
  (
    'ccc00000-0000-0000-0000-000000000003',
    'assistant',
    E'** Final Answer**\nThe engineering team budget for Q2 2025 is ₹1.2 Crores, allocated across hiring (40%), infrastructure (35%), and training (25%).\n\n** Data Quality Notes**\n CONFLICTING DATA: The roadmap mentions ₹1.35 Crores for engineering in Q2, while the budget sheet shows ₹1.2 Crores. The budget sheet is more recent (March 2025 vs January 2025), so ₹1.2 Crores is used.\n\n** Source References**\n- Team_Budget_Allocation_2025.xlsx, Page 1, Row 8\n- Product_Roadmap_H1_2025.pdf, Page 5, Section: Resource Planning\n\n** Reasoning**\nTwo sources were found with different figures. The budget allocation sheet is the more authoritative and recent source.',
    '[{"document": "Team_Budget_Allocation_2025.xlsx", "page": 1, "line": 8, "similarity": 0.9102}, {"document": "Product_Roadmap_H1_2025.pdf", "page": 5, "line": 1, "similarity": 0.8543}]'::jsonb,
    '{"duplicates": [], "conflicts": [{"field": "engineering_budget_q2", "values": [{"value": "1.2 Crores", "source": "Team_Budget_Allocation_2025.xlsx"}, {"value": "1.35 Crores", "source": "Product_Roadmap_H1_2025.pdf"}]}], "unique_sources": ["Team_Budget_Allocation_2025.xlsx", "Product_Roadmap_H1_2025.pdf"]}'::jsonb,
    now() - interval '2 hours 59 minutes'
  ),

  
  (
    'ccc00000-0000-0000-0000-000000000004',
    'user',
    'How many paid leaves do I get per year?',
    '[]'::jsonb,
    '{}'::jsonb,
    now() - interval '5 hours'
  ),
  (
    'ccc00000-0000-0000-0000-000000000004',
    'assistant',
    E'** Final Answer**\nAll full-time employees get 24 paid leaves per year: 12 casual leaves, 6 sick leaves, and 6 earned leaves. Unused earned leaves can be carried forward (max 18).\n\n** Data Quality Notes**\nNo data quality issues detected.\n\n** Source References**\n- Employee_Benefits_Summary.docx, Page 2, Section: Leave Policy\n- Company_Policy_Handbook_2025.pdf, Page 22, Section: Leave Entitlement\n\n** Reasoning**\nBoth sources confirm the same leave structure. No conflicts detected.',
    '[{"document": "Employee_Benefits_Summary.docx", "page": 2, "line": 1, "similarity": 0.9321}, {"document": "Company_Policy_Handbook_2025.pdf", "page": 22, "line": 1, "similarity": 0.8876}]'::jsonb,
    '{"duplicates": [{"text_preview": "24 paid leaves per year: 12 casual, 6 sick, 6 earned", "found_in": ["Employee_Benefits_Summary.docx", "Company_Policy_Handbook_2025.pdf"]}], "conflicts": [], "unique_sources": ["Employee_Benefits_Summary.docx", "Company_Policy_Handbook_2025.pdf"]}'::jsonb,
    now() - interval '4 hours 59 minutes'
  );


INSERT INTO email_configs (user_id, org_id, imap_server, email_address, encrypted_password, folder, is_active, last_polled_at)
VALUES
  (
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'a0000000-0000-0000-0000-000000000001',
    'imap.gmail.com',
    'ignisiahack@gmail.com',
    'ljjy byea xazh zskl',
    'INBOX',
    true,
    now() - interval '6 hours'
  );


INSERT INTO audit_log (org_id, user_id, action, details, created_at)
VALUES
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'upload',
    '{"filename": "Company_Policy_Handbook_2025.pdf", "visibility": "shared", "chunk_count": 47}'::jsonb,
    now() - interval '7 days'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'upload',
    '{"filename": "Q1_2025_Revenue_Report.xlsx", "visibility": "shared", "chunk_count": 32}'::jsonb,
    now() - interval '5 days'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'meera@ignisia.com'),
    'upload',
    '{"filename": "Team_Budget_Allocation_2025.xlsx", "visibility": "private", "chunk_count": 12}'::jsonb,
    now() - interval '3 days'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'priya@ignisia.com'),
    'query',
    '{"question": "How many paid leaves do I get per year?", "source_count": 2, "conflict_count": 0}'::jsonb,
    now() - interval '5 hours'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'email_ingest',
    '{"email_count": 1, "emails": [{"subject": "Board Meeting Notes", "from": "ceo@ignisia.com"}]}'::jsonb,
    now() - interval '6 hours'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com'),
    'query',
    '{"question": "What was our total revenue in Q1 2025?", "source_count": 1, "conflict_count": 0}'::jsonb,
    now() - interval '2 hours'
  ),
  (
    'a0000000-0000-0000-0000-000000000001',
    (SELECT id FROM profiles WHERE email = 'meera@ignisia.com'),
    'query',
    '{"question": "What is the engineering team budget for Q2?", "source_count": 2, "conflict_count": 1}'::jsonb,
    now() - interval '3 hours'
  );
