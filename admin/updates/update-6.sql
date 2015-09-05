BEGIN;

ALTER TABLE class RENAME TO dataset_class;
ALTER TABLE class_member RENAME TO dataset_class_member;

ALTER TABLE dataset_class RENAME CONSTRAINT class_pkey TO dataset_class_pkey;
ALTER TABLE dataset_class_member RENAME CONSTRAINT class_member_pkey TO dataset_class_member_pkey;

COMMIT;
