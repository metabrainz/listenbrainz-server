BEGIN;

ALTER TYPE background_tasks_type ADD VALUE 'pause_user' AFTER 'export_all_user_data';

ALTER TYPE background_tasks_type ADD VALUE 'unpause_user' AFTER 'pause_user';

COMMIT;