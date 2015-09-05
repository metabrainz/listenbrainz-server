BEGIN;

CREATE TABLE dataset (
  id          UUID,
  name        VARCHAR NOT NULL,
  description TEXT,
  author      INT, -- FK to user
  created     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);


CREATE TABLE class (
  id          SERIAL,
  name        VARCHAR NOT NULL,
  description TEXT,
  dataset     UUID    NOT NULL -- FK to dataset
);
ALTER TABLE class ADD CONSTRAINT class_pkey PRIMARY KEY (id);


CREATE TABLE class_member (
  class INT, -- FK to class
  mbid  UUID
);
ALTER TABLE class_member ADD CONSTRAINT class_member_pkey PRIMARY KEY (class, mbid);


-- FKs

ALTER TABLE dataset
  ADD CONSTRAINT dataset_fk_user
  FOREIGN KEY (author)
  REFERENCES "user" (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE class
  ADD CONSTRAINT class_fk_dataset
  FOREIGN KEY (dataset)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE class_member
  ADD CONSTRAINT class_member_fk_class
  FOREIGN KEY (class)
  REFERENCES class (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

CREATE EXTENSION "uuid-ossp";

COMMIT;
