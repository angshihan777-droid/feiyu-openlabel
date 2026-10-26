-- Existing-Postgres migration for the challenge workflow.
-- Fresh installations are created by Tortoise.generate_schemas().

BEGIN;

ALTER TABLE batch
    ADD COLUMN IF NOT EXISTS media_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE workflow_unit
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS review_assigned_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'assigned',
    ADD COLUMN IF NOT EXISTS reject_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_rejects INTEGER NOT NULL DEFAULT 2,
    ADD COLUMN IF NOT EXISTS current_reject_reason TEXT NULL,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_unit_assignee_status
    ON workflow_unit (tenant_id, assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_workflow_unit_reviewer_status
    ON workflow_unit (tenant_id, reviewer_id, status);

CREATE TABLE IF NOT EXISTS media_file (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id VARCHAR(64) NOT NULL,
    project_id BIGINT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(64) NOT NULL DEFAULT 'video/mp4',
    file_size BIGINT NOT NULL,
    duration DOUBLE PRECISION NULL,
    uploaded_by BIGINT NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ready'
);

CREATE INDEX IF NOT EXISTS idx_media_file_tenant
    ON media_file (tenant_id);
CREATE INDEX IF NOT EXISTS idx_media_file_project_created
    ON media_file (tenant_id, project_id, created_at);

CREATE TABLE IF NOT EXISTS task_submission (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id VARCHAR(64) NOT NULL,
    unit_id BIGINT NOT NULL,
    submitted_by BIGINT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    intervals JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_duration DOUBLE PRECISION NOT NULL DEFAULT 0,
    submission_date DATE NOT NULL,
    label_version INTEGER NOT NULL DEFAULT 0,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_task_submission_unit_version
        UNIQUE (tenant_id, unit_id, label_version)
);

CREATE INDEX IF NOT EXISTS idx_task_submission_date_user
    ON task_submission (tenant_id, submission_date, submitted_by);
CREATE INDEX IF NOT EXISTS idx_task_submission_valid
    ON task_submission (tenant_id, unit_id, is_valid);

CREATE TABLE IF NOT EXISTS reject_history (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id VARCHAR(64) NOT NULL,
    unit_id BIGINT NOT NULL,
    reviewer_id BIGINT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    label_version INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_reject_history_unit
    ON reject_history (tenant_id, unit_id, rejected_at);

COMMIT;
