BEGIN;

ALTER TABLE statistics.user RENAME artists    TO artist;
ALTER TABLE statistics.user RENAME releases   TO release;
ALTER TABLE statistics.user RENAME recordings TO recording;


ALTER TABLE statistics.artist RENAME releases   TO release;
ALTER TABLE statistics.artist RENAME recordings TO recording;
ALTER TABLE statistics.artist RENAME users      TO listener;


ALTER TABLE statistics.release RENAME recordings TO recording;
ALTER TABLE statistics.release RENAME users      TO listener;

ALTER TABLE statistics.recording RENAME users_all_time TO listener;

COMMIT;
