-- Migration 0002: Audit event indexes for analytics queries
-- Safe to re-run: all statements use IF NOT EXISTS.
-- Apply with: psql $HOLOGRES_DSN -f infra/postgres/migrations/0002_audit_indexes.sql

-- actor_user_id: not a column in audit_events_flat; queries use actor_name as the actor field.
-- Index on actor_name for per-user audit queries (matches AuditLogger._write_pg logic)
CREATE INDEX IF NOT EXISTS idx_audit_events_flat_actor
    ON audit_events_flat (actor_name, created_at DESC);

-- event_type + time: for compliance dashboard filtering by event category
CREATE INDEX IF NOT EXISTS idx_audit_events_flat_type_time
    ON audit_events_flat (event_type, created_at DESC);

-- target_type + target_id: for "what happened to this object" queries
CREATE INDEX IF NOT EXISTS idx_audit_events_flat_target
    ON audit_events_flat (target_type, target_id);
