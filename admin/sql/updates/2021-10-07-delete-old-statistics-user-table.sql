BEGIN;
DROP TABLE IF EXISTS statistics.user;

ALTER TABLE statistics.user_new RENAME TO "user";
ALTER SEQUENCE statistics.user_new_id_seq RENAME TO user_id_seq;
ALTER TABLE statistics.user RENAME CONSTRAINT stats_user_new_pkey TO stats_user_pkey;
ALTER TABLE statistics.user RENAME CONSTRAINT user_stats_new_user_id_foreign_key TO user_stats_user_id_foreign_key;
ALTER INDEX statistics.user_id_ndx__user_stats_new RENAME TO user_id_ndx__user_stats;
COMMIT;
