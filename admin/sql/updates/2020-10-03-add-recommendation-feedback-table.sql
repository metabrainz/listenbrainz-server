BEGIN;

-- Create new table
CREATE TABLE recommendation_feedback (
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_mbid          UUID NOT NULL,
    rating                  recommendation_feedback_type_enum NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create primary key
ALTER TABLE recommendation_feedback ADD CONSTRAINT recommendation_feedback_pkey PRIMARY KEY (id);

-- Create foreign key
ALTER TABLE recommendation_feedback
    ADD CONSTRAINT recommendation_feedback_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

-- Create unique index
CREATE UNIQUE INDEX user_id_rec_mbid_ndx_feedback ON recommendation_feedback (user_id, recording_mbid);

CREATE INDEX rating_recommendation_feedback ON recommendation_feedback (rating);

COMMIT;
