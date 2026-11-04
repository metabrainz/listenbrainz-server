-- Reads switch to this table in the same deploy that starts maintaining it, so it must be
-- populated BEFORE that deploy, or every count and timestamp bound is wrong until it is:
--   1. Run this script in the listens DB.
--   2. With the new image, in a one-off container while the old code still serves traffic, run
--      `manage.py recalculate_all_user_data`. Users without a row are counted once and created.
--   3. Deploy the new code (web, timescale writer, cron).
--   4. Run `manage.py recalculate_all_user_data` again. The old code did not update this table,
--      so it corrects users whose listens were ingested or deleted between steps 2 and 3. Only
--      those users are recounted and locked. Until it finishes, their counts are slightly low.
-- Rollback: the old code reads Timescale's listen_user_metadata, which the new code no longer
-- updates. Run the old `manage.py recalculate_all_user_data` after rolling back.
BEGIN;

CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL,
    min_listened_at     TIMESTAMP WITH TIME ZONE,
    max_listened_at     TIMESTAMP WITH TIME ZONE
);

ALTER TABLE listen_user_metadata ADD CONSTRAINT listen_user_metadata_pkey PRIMARY KEY (user_id);

COMMIT;
