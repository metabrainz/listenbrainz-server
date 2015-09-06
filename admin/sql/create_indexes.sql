BEGIN;

CREATE UNIQUE INDEX auth_token_ndx_user ON "user" (auth_token);

COMMIT;
