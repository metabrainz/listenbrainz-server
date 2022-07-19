BEGIN;
ALTER TABLE mbid_mapping ADD COLUMN check_again TIMESTAMP WITH TIME ZONE;
COMMIT;

-- first time adding the column need to set check_again column to a non-null
-- value so that next time the msid comes in the rechecking stuff kicks in
BEGIN;
UPDATE mbid_mapping SET check_again = NOW() WHERE match_type = 'no_match';
COMMIT;
