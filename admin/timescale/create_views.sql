BEGIN;

-- create a materialized view of the top mappings of a recording msid. top mappings are chosen
-- by the highest number of users that have added it. if multiple mappings have same count, break
-- ties by preferring the mapping that was created most recently.
CREATE MATERIALIZED VIEW mbid_manual_mapping_top AS (
    SELECT DISTINCT ON (recording_msid)
           recording_msid
         , recording_mbid
      FROM mbid_manual_mapping
  GROUP BY recording_msid
         , recording_mbid
  ORDER BY recording_msid
         , count(*) DESC
         , max(created) DESC
);

CREATE INDEX mbid_manual_mapping_top_idx ON mbid_manual_mapping_top (recording_msid) INCLUDE (recording_mbid);

COMMIT;
