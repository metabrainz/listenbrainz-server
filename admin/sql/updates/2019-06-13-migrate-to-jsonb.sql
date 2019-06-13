BEGIN;

ALTER TABLE recording DROP CONSTRAINT recording_fk_recording_json;

ALTER TABLE recording_json RENAME TO recording_json_tofix;

SELECT id, regexp_replace(data::text, '\\u0000', '', 'g')::JSONB AS data, data_sha256, meta_sha256 
  INTO recording_json 
  FROM recording_json_tofix;

ALTER TABLE recording_json
  ALTER COLUMN data
  SET DATA TYPE jsonb
  USING data::jsonb;

ALTER TABLE recording_json ADD CONSTRAINT recording_json_pkey PRIMARY KEY (id);

CREATE OR REPLACE FUNCTION array_sort(uuid[])
RETURNS uuid[] AS $sorted_array$
DECLARE
    sorted_array uuid[];
BEGIN
    SELECT ARRAY(SELECT unnest($1) ORDER BY 1) INTO sorted_array;
    RETURN sorted_array;
END
$sorted_array$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION convert_json_array_to_sorted_uuid_array(json)
RETURNS uuid[] AS $converted_array$
DECLARE
    converted_array uuid[];
BEGIN
    SELECT array_sort(array_agg(elements)::uuid[]) || ARRAY[]::uuid[] INTO converted_array
    FROM json_array_elements_text($1) elements;
    RETURN converted_array;
END
$converted_array$ LANGUAGE plpgsql IMMUTABLE;

CREATE INDEX artist_mbid_array_ndx_recording_json ON recording_json (convert_json_array_to_sorted_uuid_array((data -> 'artist_mbids')::JSON));
CREATE INDEX recording_mbid_ndx_recording_json ON recording_json ((data ->> 'recording_mbid'));
CREATE INDEX artist_mbid_ndx_recording_json ON recording_json ((data ->> 'artist_mbids'));
CREATE INDEX release_mbid_ndx_recording_json ON recording_json ((data ->> 'release_mbid'));

ALTER TABLE recording
  ADD CONSTRAINT recording_fk_recording_json
  FOREIGN KEY (data)
  REFERENCES recording_json (id);

DROP TABLE recording_json_tofix;

COMMIT;
