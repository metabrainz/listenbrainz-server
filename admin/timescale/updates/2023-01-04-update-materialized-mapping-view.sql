BEGIN;

DROP MATERIALIZED VIEW mbid_manual_mapping_top;

-- create a materialized view of the top mappings of a recording msid. top mappings are chosen
-- by the highest number of users that have added it. if multiple mappings have same count, break
-- ties by preferring the mapping that was created most recently. to avoid abuse, mappings are only
-- considered for this view if at least 3 separate users created those.
CREATE MATERIALIZED VIEW mbid_manual_mapping_top AS (
    SELECT DISTINCT ON (recording_msid)
           recording_msid
         , recording_mbid
      FROM mbid_manual_mapping
  GROUP BY recording_msid
         , recording_mbid
    HAVING count(DISTINCT user_id) >= 3
  ORDER BY recording_msid
         , count(*) DESC
         , max(created) DESC
);

COMMIT;
