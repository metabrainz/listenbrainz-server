BEGIN;

CREATE TABLE recommendation (
	user_id 			INTEGER NOT NULL, --PK and FK to "user".id
	daily_delight 		JSONB,
	listened_to 		BOOL DEFAULT FALSE,
	last_updated 		TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

--Create primary key
ALTER TABLE recommendation ADD CONSTRAINT rec_pkey PRIMARY KEY (user_id);

--Create foreign key
ALTER TABLE recommendation ADD CONSTRAINT user_rec_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);
COMMIT;