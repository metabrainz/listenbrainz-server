BEGIN;

ALTER TABLE "user" DROP COLUMN user_login_id;
ALTER TABLE "user" ADD COLUMN login_id TEXT NOT NULL DEFAULT uuid_generate_v4()::text;

UPDATE "user"
   SET login_id = id::text;

ALTER TABLE "user" ADD CONSTRAINT user_login_id_key UNIQUE (login_id);
CREATE UNIQUE INDEX login_id_ndx_user ON "user" (login_id);

COMMIT;

