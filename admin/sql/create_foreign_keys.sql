BEGIN;

ALTER TABLE tokens ADD CONSTRAINT tokens_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);
ALTER TABLE sessions ADD CONSTRAINT sessions_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
