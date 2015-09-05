BEGIN;

CREATE TABLE incremental_dumps (
  id      SERIAL,
  created TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE incremental_dumps ADD CONSTRAINT incremental_dumps_pkey PRIMARY KEY (id);

COMMIT;
