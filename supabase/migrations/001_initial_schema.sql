-- ============================================================
-- Ignisia26 — Supabase Database Schema
-- Enterprise RAG Pipeline with RBAC & Conflict Detection
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector for embeddings


-- ============================================================
-- 1. ORGANIZATIONS
-- ============================================================
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,             -- url-friendly identifier
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);


-- ============================================================
-- 2. PROFILES  (extends Supabase auth.users)
-- ============================================================
CREATE TABLE profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('director', 'manager', 'employee')),
    reports_to      UUID REFERENCES profiles(id) ON DELETE SET NULL,
    email           TEXT,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_profiles_org ON profiles(org_id);
CREATE INDEX idx_profiles_reports_to ON profiles(reports_to);
CREATE INDEX idx_profiles_role ON profiles(role);


-- ============================================================
-- 3. DOCUMENTS  (uploaded file metadata)
-- ============================================================
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id        UUID REFERENCES profiles(id) ON DELETE SET NULL,  -- NULL = shared/org-wide
    filename        TEXT NOT NULL,
    file_type       TEXT NOT NULL,                 -- pdf, docx, xlsx, csv, txt, eml
    file_size_bytes BIGINT,
    visibility      TEXT NOT NULL DEFAULT 'shared' CHECK (visibility IN ('shared', 'private')),
    source_type     TEXT NOT NULL DEFAULT 'upload' CHECK (source_type IN ('upload', 'email')),
    storage_path    TEXT,                          -- Supabase Storage path
    chunk_count     INT DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_documents_org ON documents(org_id);
CREATE INDEX idx_documents_owner ON documents(owner_id);
CREATE INDEX idx_documents_status ON documents(status);


-- ============================================================
-- 4. CHUNKS  (document chunks with vector embeddings)
-- ============================================================
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    embedding       vector(384),                   -- all-MiniLM-L6-v2 = 384 dims
    page_number     INT DEFAULT 1,
    line_number     INT DEFAULT 1,
    section         TEXT DEFAULT '',
    date_added      DATE,                          -- source date (email date or ingestion date)
    token_count     INT,
    chunk_index     INT NOT NULL,                  -- ordering within the document
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_org ON chunks(org_id);

-- HNSW index for fast vector similarity search (cosine distance)
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);


-- ============================================================
-- 5. CONVERSATIONS  (chat sessions)
-- ============================================================
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title           TEXT DEFAULT 'New Conversation',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);


-- ============================================================
-- 6. MESSAGES  (chat messages within a conversation)
-- ============================================================
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    sources         JSONB DEFAULT '[]'::jsonb,     -- source references returned by RAG
    analysis        JSONB DEFAULT '{}'::jsonb,     -- duplicates, conflicts analysis
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);


-- ============================================================
-- 7. EMAIL CONFIGS  (IMAP polling settings per user)
-- ============================================================
CREATE TABLE email_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    imap_server     TEXT NOT NULL,
    email_address   TEXT NOT NULL,
    encrypted_password TEXT NOT NULL,               -- store encrypted, decrypt server-side
    folder          TEXT DEFAULT 'INBOX',
    is_active       BOOLEAN DEFAULT true,
    last_polled_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)                                -- one config per user
);


-- ============================================================
-- 8. AUDIT LOG  (track queries and key actions)
-- ============================================================
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES profiles(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,                  -- 'query', 'upload', 'delete', 'email_ingest'
    details         JSONB DEFAULT '{}'::jsonb,      -- flexible payload
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_org ON audit_log(org_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at);


-- ============================================================
-- 9. HELPER FUNCTIONS
-- ============================================================

-- Recursive function: get all subordinate user IDs for a given user
CREATE OR REPLACE FUNCTION get_all_subordinates(manager_id UUID)
RETURNS SETOF UUID
LANGUAGE sql
STABLE
AS $$
    WITH RECURSIVE subordinates AS (
        SELECT id FROM profiles WHERE reports_to = manager_id
        UNION ALL
        SELECT p.id FROM profiles p
        INNER JOIN subordinates s ON p.reports_to = s.id
    )
    SELECT id FROM subordinates;
$$;


-- Semantic search function: find similar chunks with access control baked in
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding  vector(384),
    match_count      INT DEFAULT 15,
    match_threshold  FLOAT DEFAULT 0.3,
    p_org_id         UUID DEFAULT NULL,
    p_user_id        UUID DEFAULT NULL
)
RETURNS TABLE (
    id              UUID,
    document_id     UUID,
    content         TEXT,
    page_number     INT,
    line_number     INT,
    section         TEXT,
    date_added      DATE,
    similarity      FLOAT,
    filename        TEXT,
    file_type       TEXT,
    owner_id        UUID,
    visibility      TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    user_role TEXT;
BEGIN
    -- Get the requesting user's role
    SELECT p.role INTO user_role FROM profiles p WHERE p.id = p_user_id;

    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.content,
        c.page_number,
        c.line_number,
        c.section,
        c.date_added,
        1 - (c.embedding <=> query_embedding) AS similarity,
        d.filename,
        d.file_type,
        d.owner_id,
        d.visibility
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.org_id = p_org_id
      AND d.status = 'ready'
      AND 1 - (c.embedding <=> query_embedding) > match_threshold
      -- Access control filter
      AND (
          -- Shared documents: everyone can see
          d.visibility = 'shared'
          -- Own documents: always visible
          OR d.owner_id = p_user_id
          -- Director: sees everything
          OR user_role = 'director'
          -- Manager: sees subordinates' docs
          OR (user_role = 'manager' AND d.owner_id IN (SELECT get_all_subordinates(p_user_id)))
      )
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================================
-- 10. ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- ── Organizations: users can read their own org ──
CREATE POLICY "Users can view their organization"
    ON organizations FOR SELECT
    USING (id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid()));

-- ── Profiles: users can see profiles in their org ──
CREATE POLICY "Users can view profiles in their org"
    ON profiles FOR SELECT
    USING (org_id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid()));

CREATE POLICY "Users can update their own profile"
    ON profiles FOR UPDATE
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- ── Documents: visibility-based access ──
CREATE POLICY "Users can view accessible documents"
    ON documents FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid())
        AND (
            visibility = 'shared'
            OR owner_id = auth.uid()
            OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'director'
            OR (
                (SELECT role FROM profiles WHERE id = auth.uid()) = 'manager'
                AND owner_id IN (SELECT get_all_subordinates(auth.uid()))
            )
        )
    );

CREATE POLICY "Users can insert documents in their org"
    ON documents FOR INSERT
    WITH CHECK (org_id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid()));

CREATE POLICY "Users can delete their own documents"
    ON documents FOR DELETE
    USING (owner_id = auth.uid() OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'director');

-- ── Chunks: inherit document access (read via match_chunks function mostly) ──
CREATE POLICY "Users can view chunks of accessible documents"
    ON chunks FOR SELECT
    USING (
        document_id IN (SELECT id FROM documents)  -- relies on document RLS
    );

CREATE POLICY "Users can insert chunks in their org"
    ON chunks FOR INSERT
    WITH CHECK (org_id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid()));

-- ── Conversations: users see only their own ──
CREATE POLICY "Users can manage their own conversations"
    ON conversations FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ── Messages: users see messages in their own conversations ──
CREATE POLICY "Users can manage messages in their conversations"
    ON messages FOR ALL
    USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()))
    WITH CHECK (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));

-- ── Email configs: users manage their own ──
CREATE POLICY "Users can manage their own email config"
    ON email_configs FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ── Audit log: directors can view org audit log, others see their own ──
CREATE POLICY "Users can view relevant audit logs"
    ON audit_log FOR SELECT
    USING (
        user_id = auth.uid()
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'director'
    );

CREATE POLICY "System can insert audit logs"
    ON audit_log FOR INSERT
    WITH CHECK (org_id IN (SELECT org_id FROM profiles WHERE profiles.id = auth.uid()));


-- ============================================================
-- 11. AUTO-UPDATE TIMESTAMPS TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_organizations_updated BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_profiles_updated BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_documents_updated BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_email_configs_updated BEFORE UPDATE ON email_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_conversations_updated BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 12. AUTO-CREATE PROFILE ON SIGNUP (via auth trigger)
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, org_id, full_name, role, email)
    VALUES (
        NEW.id,
        (NEW.raw_user_meta_data->>'org_id')::UUID,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'role', 'employee'),
        NEW.email
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();


-- ============================================================
-- 13. STORAGE BUCKET FOR UPLOADED DOCUMENTS
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies: users can upload/read docs in their org folder
CREATE POLICY "Users can upload documents"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] IN (
            SELECT org_id::text FROM profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can read documents in their org"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] IN (
            SELECT org_id::text FROM profiles WHERE id = auth.uid()
        )
    );
