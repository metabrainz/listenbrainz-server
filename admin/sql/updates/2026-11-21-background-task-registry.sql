-- Stop the background_tasks containers before running this, it releases every claimed task.
BEGIN;

DROP INDEX background_tasks_user_id_task_type_uniq_idx;

ALTER TABLE background_tasks
    ADD COLUMN due_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ADD COLUMN attempts     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN failed_at    TIMESTAMP WITH TIME ZONE,
    ADD COLUMN last_error   TEXT;

-- deferred tasks used to keep a backdated claim; they are plain due rows now
UPDATE background_tasks SET claimed_at = NULL;

CREATE UNIQUE INDEX background_tasks_user_id_delete_task_uniq_idx ON background_tasks (user_id, task) WHERE task IN ('delete_user', 'delete_listens') AND failed_at IS NULL;
CREATE UNIQUE INDEX background_tasks_user_id_running_uniq_idx ON background_tasks (user_id) WHERE claimed_at IS NOT NULL;

COMMIT;
