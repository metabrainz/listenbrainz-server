ALTER TYPE background_tasks_type ADD VALUE 'export_user';

BEGIN;

DROP INDEX background_tasks_user_id_task_type_idx;
CREATE UNIQUE INDEX background_tasks_user_id_task_type_uniq_idx ON background_tasks (user_id, task);

CREATE TABLE user_data_export (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    filename            TEXT NOT NULL,
    available_until     TIMESTAMPTZ NOT NULL,
    created             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_data_export ADD CONSTRAINT user_data_export_id_pkey PRIMARY KEY (id);

ALTER TABLE user_data_export
    ADD CONSTRAINT user_data_export_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_data_export_user_id_idx ON user_data_export (user_id);

COMMIT;
