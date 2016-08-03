BEGIN;

ALTER TABLE api_compat.token ADD CONSTRAINT token_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);
ALTER TABLE api_compat.session ADD CONSTRAINT session_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
