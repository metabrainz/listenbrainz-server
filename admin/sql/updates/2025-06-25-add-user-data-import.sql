ALTER TYPE background_tasks_type ADD VALUE 'import_listens';

CREATE TYPE user_data_import_service_type AS ENUM ('spotify', 'applemusic', 'listenbrainz');

CREATE TABLE user_data_import (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    user_id             INTEGER NOT NULL,
    service             user_data_import_service_type NOT NULL,
    metadata            JSONB,
    file_path           TEXT NOT NULL,
    from_date           TIMESTAMPTZ NOT NULL DEFAULT 'epoch',
    to_date             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_data_import ADD CONSTRAINT user_data_import_id_pkey PRIMARY KEY (id);

ALTER TABLE user_data_import
    ADD CONSTRAINT user_data_import_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX user_data_import_user_id_idx ON user_data_import (user_id);
CREATE UNIQUE INDEX user_data_import_deduplicate_waiting_idx ON user_data_import (user_id, service) WHERE metadata->>'status' IN ('waiting', 'in_progress');

COMMIT;
