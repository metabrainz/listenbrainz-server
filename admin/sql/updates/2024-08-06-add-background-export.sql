ALTER TYPE background_tasks_type ADD VALUE 'export_all_user_data';
CREATE TYPE user_data_export_type_type AS ENUM ('export_all_user_data');
CREATE TYPE user_data_export_status_type AS ENUM ('in_progress', 'waiting', 'completed', 'failed');

BEGIN;

DROP INDEX background_tasks_user_id_task_type_idx;
CREATE UNIQUE INDEX background_tasks_user_id_task_type_uniq_idx ON background_tasks (user_id, task);

ALTER TABLE background_tasks ADD COLUMN metadata JSONB;

CREATE TABLE user_data_export (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    type                user_data_export_type_type NOT NULL,
    status              user_data_export_status_type NOT NULL,
    progress            TEXT,
    filename            TEXT,
    available_until     TIMESTAMPTZ,
    created             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_data_export ADD CONSTRAINT user_data_export_id_pkey PRIMARY KEY (id);

ALTER TABLE user_data_export
    ADD CONSTRAINT user_data_export_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_data_export_user_id_idx ON user_data_export (user_id);
CREATE UNIQUE INDEX user_data_export_deduplicate_waiting_idx ON user_data_export (user_id, type) WHERE status = 'waiting' OR status = 'in_progress';

COMMIT;
