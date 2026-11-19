-- 검토용 미적용 패치. 자동 실행·기존 Alembic 이력 수정 금지.
-- 공통 담당자가 새 마이그레이션으로 옮긴 뒤 적용한다. 데이터 삭제 구문은 없다.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

ALTER TABLE mails ADD CONSTRAINT uq_f1_mail_owner UNIQUE (mail_id, user_id, account_id);

CREATE TABLE f1_mail_analysis (
    mail_id text PRIMARY KEY,
    user_id text NOT NULL,
    account_id text NOT NULL,
    category text CHECK (category IN
        ('work_request','meeting','approval','report_share','notice','external','newsletter')),
    user_label text CHECK (user_label IN
        ('work_request','meeting','approval','report_share','notice','external','newsletter')),
    summary text,
    action_items jsonb NOT NULL DEFAULT '[]',
    needs_reply boolean,
    priority text CHECK (priority IN ('high','normal','low')),
    priority_reason text,
    entities jsonb NOT NULL DEFAULT '{"projects":[],"orgs":[],"people":[]}',
    events jsonb NOT NULL DEFAULT '[]',
    evidence_spans jsonb NOT NULL DEFAULT '[]',
    failure_code text,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 2),
    llm_provider text,
    llm_model text,
    llm_mode text CHECK (llm_mode IN ('live','test')),
    embedding_provider text,
    embedding_model text,
    embedding_mode text CHECK (embedding_mode IN ('live','test')),
    embedding_dimensions integer CHECK (embedding_dimensions BETWEEN 1 AND 4096),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (mail_id, user_id, account_id),
    FOREIGN KEY (mail_id, user_id, account_id)
        REFERENCES mails (mail_id, user_id, account_id) ON DELETE CASCADE
);

CREATE TABLE f1_mail_chunks (
    chunk_id text PRIMARY KEY,
    mail_id text NOT NULL,
    user_id text NOT NULL,
    account_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('body','summary')),
    seq integer NOT NULL CHECK (seq >= 0),
    text text NOT NULL,
    embedding vector NOT NULL,
    embedding_dimensions integer NOT NULL CHECK (embedding_dimensions BETWEEN 1 AND 4096),
    embedding_provider text NOT NULL,
    embedding_model text NOT NULL,
    embedding_mode text NOT NULL CHECK (embedding_mode IN ('live','test')),
    received_at timestamptz NOT NULL,
    category text NOT NULL CHECK (category IN
        ('work_request','meeting','approval','report_share','notice','external','newsletter')),
    UNIQUE (mail_id, kind, seq),
    CHECK (vector_dims(embedding) = embedding_dimensions),
    FOREIGN KEY (mail_id, user_id, account_id)
        REFERENCES f1_mail_analysis (mail_id, user_id, account_id) ON DELETE CASCADE
);

CREATE INDEX ix_f1_chunks_scope
    ON f1_mail_chunks (user_id, account_id, received_at, category);

CREATE TABLE f1_category_feedback (
    feedback_id bigserial PRIMARY KEY,
    mail_id text NOT NULL,
    user_id text NOT NULL,
    account_id text NOT NULL,
    from_addr text NOT NULL,
    subject text NOT NULL,
    user_label text NOT NULL CHECK (user_label IN
        ('work_request','meeting','approval','report_share','notice','external','newsletter')),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (mail_id, user_id, account_id)
        REFERENCES f1_mail_analysis (mail_id, user_id, account_id) ON DELETE CASCADE
);

CREATE INDEX ix_f1_feedback_sender
    ON f1_category_feedback (user_id, account_id, from_addr, feedback_id DESC);
