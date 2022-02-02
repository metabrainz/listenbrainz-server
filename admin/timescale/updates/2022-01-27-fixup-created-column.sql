BEGIN;

-- created field was not always a part of listen table. at the time it was added, it was set to 'epoch' for pre-existing
-- rows and left as nullable. however, it makes more sense to set created according to listened_at field. we can also
-- add the not null constraint.
UPDATE listen
   SET created = to_timestamp(listened_at)
 WHERE created = 'epoch';

ALTER TABLE listen ALTER COLUMN created SET NOT NULL;
COMMIT;
