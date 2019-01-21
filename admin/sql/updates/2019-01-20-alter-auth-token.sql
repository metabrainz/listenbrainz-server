BEGIN;

ALTER TABLE "user" ALTER COLUMN auth_token TYPE UUID USING auth_token::UUID,
ALTER COLUMN auth_token SET NOT NULL;

ALTER TABLE "user" ALTER COLUMN auth_token SET DEFAULT uuid_generate_v4();

COMMIT;