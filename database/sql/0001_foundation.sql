-- المرحلة 1: الأساسات (الإعدادات + سجل التدقيق + أحداث النظام)
-- تعمل داخل مخطط المشروع فقط ولا تلمس أي جدول قديم.

CREATE TABLE store_settings (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by_admin_id bigint
);

INSERT INTO store_settings (key, value) VALUES
    ('store_open', 'false'),
    ('launch_activated', 'false'),
    ('unpaid_timeout_minutes', '30'),
    ('review_request_days_before', '3'),
    ('admin_session_minutes', '30'),
    ('pin_max_attempts', '5'),
    ('pin_lockout_minutes', '15')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE audit_log (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    admin_id bigint,
    admin_name text,
    action text NOT NULL,
    entity_type text,
    entity_id text,
    old_value jsonb,
    new_value jsonb,
    reason text
);

CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_created ON audit_log (created_at DESC);

CREATE FUNCTION prevent_audit_log_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$;

CREATE TRIGGER trg_audit_log_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_change();

CREATE TRIGGER trg_audit_log_no_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_audit_log_change();

CREATE TABLE system_events (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    level text NOT NULL,
    component text NOT NULL,
    message text NOT NULL,
    details jsonb
);

CREATE INDEX idx_system_events_created ON system_events (created_at DESC);
