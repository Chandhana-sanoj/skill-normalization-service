
-- Separate platform-level Super Admin accounts
CREATE TABLE IF NOT EXISTS public.super_admin (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Allow Super Admin to deactivate or soft-delete organizations
ALTER TABLE public.organization
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE public.organization
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Allow Super Admin to deactivate organization users
ALTER TABLE public.organization_user
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Organization skill submissions for central catalogue review
CREATE TABLE IF NOT EXISTS public.skill_catalogue_submission (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL
        REFERENCES public.organization(id),
    organization_skill_id BIGINT NOT NULL
        REFERENCES public.organization_skill(id) ON DELETE CASCADE,
    submitted_by BIGINT
        REFERENCES public.organization_user(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'approved_canonical',
            'approved_alias',
            'rejected'
        )),
    review_type TEXT,
    canonical_skill_id BIGINT
        REFERENCES public.canonical_skill(id),
    review_reason TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by BIGINT
        REFERENCES public.super_admin(id)
);

CREATE INDEX IF NOT EXISTS idx_skill_submission_status
ON public.skill_catalogue_submission(status, submitted_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_skill_submission_pending_skill
ON public.skill_catalogue_submission(organization_skill_id)
WHERE status = 'pending';

-- Record important Super Admin actions
CREATE TABLE IF NOT EXISTS public.super_admin_audit_log (
    id BIGSERIAL PRIMARY KEY,
    super_admin_id BIGINT REFERENCES public.super_admin(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_super_admin_audit_created
ON public.super_admin_audit_log(created_at DESC);
