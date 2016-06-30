BEGIN;

ALTER TABLE token ADD CONSTRAINT token_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);
ALTER TABLE session ADD CONSTRAINT session_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
