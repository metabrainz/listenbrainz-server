Query to generate a subset of listens by year:

SELECT
  *
FROM
  [listenbrainz:listenbrainz.listen]
WHERE
  YEAR(listened_at) = 2017
  AND recording_mbid != "";


Query to generate recording_id and recording_mbid table from listens_<year> table:

SELECT
  ROW_NUMBER() OVER() AS recording_id,
  recording_mbid,
  track_name
FROM
  [listenbrainz:explore.listens_2017] 
GROUP BY
  recording_mbid,
  track_name

Query to generate user_ids:

SELECT
  ROW_NUMBER() OVER() AS user_id,
  user_name
FROM
  [listenbrainz:explore.listens_2017]
GROUP BY
  user_name

Query to generate play_counts from the table above:

SELECT
  COUNT(l.recording_mbid) AS play_count,
  uid.user_id AS user_id,
  rid.recording_id AS recording_id
FROM
  [listenbrainz:explore.listens_2017] AS l
JOIN
  [listenbrainz:explore.listens_2017_recording_id] AS rid
ON
  l.recording_mbid = rid.recording_mbid
JOIN
  [listenbrainz:explore.listens_2017_user_id] AS uid
ON
  l.user_name = uid.user_name
GROUP BY
  user_id,
  recording_id,
ORDER BY
  user_id,
  play_count DESC


Query to check the joins to make sure they are correct

SELECT
  p.play_count AS play_count,
  u.user_name AS user_name,
  u.user_id AS user_id,
  r.recording_id AS recording_id,
  r.track_name AS track_name
FROM
  [listenbrainz:explore.listens_2017_playcounts] AS p
JOIN
  [listenbrainz:explore.listens_2017_user_id] AS u
ON
  u.user_id = p.user_id
JOIN
  [listenbrainz:explore.listens_2017_recording_id] AS r
ON
  r.recording_id = p.recording_id
WHERE
  user_name = 'rob'
ORDER BY
  play_count desc
