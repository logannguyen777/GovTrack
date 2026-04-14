-- ============================================================
-- GovFlow: Hologres / PostgreSQL Schema
-- Local: pgvector extension replaces Proxima
-- ============================================================

-- Enable vector extension (pgvector locally, Proxima on Hologres)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(100) UNIQUE NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    password_hash   VARCHAR(200) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'officer',
        -- roles: admin, leader, officer, public_viewer
    clearance_level INTEGER NOT NULL DEFAULT 0,
        -- 0=Binh thuong (UNCLASSIFIED), 1=Han che (CONFIDENTIAL), 2=Mat (SECRET), 3=Toi mat (TOP_SECRET)
        -- Matches ClearanceLevel IntEnum in backend/src/models/enums.py
    departments     TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_departments ON users USING GIN (departments);

-- ============================================================
-- law_chunks: vector-indexed law article chunks
-- ============================================================
CREATE TABLE IF NOT EXISTS law_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    law_id          VARCHAR(100) NOT NULL,
        -- e.g. "28/2009/QH12", "50/2014/QH13"
    article_number  VARCHAR(50) NOT NULL,
        -- e.g. "Dieu 35", "Dieu 1"
    clause_path     VARCHAR(200),
        -- e.g. "Dieu 35 > Khoan 2 > Diem a"
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    title           TEXT,
    content         TEXT NOT NULL,
    embedding       vector(1536),
        -- Qwen3-Embedding v3, 1536 dimensions
        -- Populated by scripts/embed_chunks.py
    metadata        JSONB DEFAULT '{}',
        -- {effective_date, status, classification, issuing_body, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector similarity index is created AFTER data load in embed_chunks.py
-- For pgvector local dev:
--   CREATE INDEX idx_law_chunks_embedding ON law_chunks
--       USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
-- For Hologres cloud:
--   CALL set_table_property('law_chunks', 'proxima_vectors', ...);

CREATE INDEX IF NOT EXISTS idx_law_chunks_law_id ON law_chunks (law_id);
CREATE INDEX IF NOT EXISTS idx_law_chunks_article ON law_chunks (article_number);

-- ============================================================
-- analytics_cases: case processing metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(100) NOT NULL,
    department_id   VARCHAR(100) NOT NULL,
    tthc_code       VARCHAR(100),
    status          VARCHAR(50) NOT NULL DEFAULT 'submitted',
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    processing_days INTEGER,
    sla_days        INTEGER,
    is_overdue      BOOLEAN DEFAULT FALSE,
    agent_steps     INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_analytics_cases_dept ON analytics_cases (department_id);
CREATE INDEX IF NOT EXISTS idx_analytics_cases_status ON analytics_cases (status);
CREATE INDEX IF NOT EXISTS idx_analytics_cases_submitted ON analytics_cases (submitted_at);

-- ============================================================
-- analytics_agents: per-agent-step metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(100) NOT NULL,
    agent_name      VARCHAR(100) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    tool_calls      INTEGER DEFAULT 0,
    status          VARCHAR(50) NOT NULL DEFAULT 'running',
        -- running, completed, failed, retrying
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_analytics_agents_case ON analytics_agents (case_id);
CREATE INDEX IF NOT EXISTS idx_analytics_agents_name ON analytics_agents (agent_name);

-- ============================================================
-- notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    body            TEXT,
    category        VARCHAR(50) NOT NULL DEFAULT 'info',
        -- info, action_required, alert, system
    link            VARCHAR(500),
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at DESC);

-- ============================================================
-- audit_events_flat: denormalized audit log (mirrors GDB AuditEvent)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_events_flat (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(100) NOT NULL,
        -- case.created, document.uploaded, agent.completed, permission.denied, ...
    actor_id        UUID,
    actor_name      VARCHAR(200),
    target_type     VARCHAR(100),
    target_id       VARCHAR(200),
    case_id         VARCHAR(200),
    department_id   VARCHAR(100),
    details         JSONB DEFAULT '{}',
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events_flat (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events_flat (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_case ON audit_events_flat (case_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events_flat (created_at DESC);

-- ============================================================
-- templates_nd30: Nghi dinh 30 document templates
-- ============================================================
CREATE TABLE IF NOT EXISTS templates_nd30 (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_code   VARCHAR(100) UNIQUE NOT NULL,
        -- e.g. "mau_01_nd30", "mau_02_nd30"
    template_name   VARCHAR(500) NOT NULL,
    category        VARCHAR(100),
    content_html    TEXT NOT NULL,
    placeholders    JSONB DEFAULT '[]',
        -- [{"key": "ho_ten", "label": "Ho va ten", "type": "string"}, ...]
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_templates_code ON templates_nd30 (template_code);

-- ============================================================
-- Seed users for development / demo
-- Passwords: SHA256 hex digest of "demo"
-- sha256("demo") = 2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea
-- ============================================================
INSERT INTO users (username, full_name, email, password_hash, role, clearance_level, departments) VALUES
    ('admin', 'System Administrator', 'admin@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'admin', 3, '{"DEPT-ADMIN"}'),
    ('cv_qldt', 'Nguyen Van Chuyen Vien', 'cv_qldt@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'officer', 1, '{"DEPT-QLDT"}'),
    ('ld_phong', 'Tran Thi Lanh Dao', 'ld_phong@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'leader', 2, '{"DEPT-QLDT","DEPT-TNMT"}'),
    ('staff_intake', 'Le Van Tiep Nhan', 'intake@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'officer', 0, '{"DEPT-TNMT"}'),
    ('legal_expert', 'Pham Thi Phap Ly', 'legal@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'officer', 2, '{"DEPT-PHAPCHE"}'),
    ('security_officer', 'Hoang Van Bao Mat', 'security@govflow.vn',
     '2a97516c354b68848cdbd8f54a226a0a55b21ed138e207ad6c5cbb9c00aa5aea',
     'admin', 3, '{"DEPT-ADMIN","DEPT-ANNINH"}')
ON CONFLICT (username) DO NOTHING;
