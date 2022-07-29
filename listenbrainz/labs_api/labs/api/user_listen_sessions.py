from datasethoster import Query
from flask import current_app
from markupsafe import Markup
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import psycopg2

from listenbrainz import db
from listenbrainz.db import timescale


class UserListensSessionQuery(Query):
    """ Display sessions of user's listens as sessions for given time period """

    def names(self):
        return "sessions-viewer", "ListenBrainz Session Viewer"

    def inputs(self):
        return ['user_name', 'from_ts', 'to_ts', 'threshold']

    def introduction(self):
        return """This page allows you to view the listens of the given time period for a user distributed
         into sessions. Listens are considered to belong to same session if the time difference between any
         two consecutive listens in that set is less than a given threshold."""

    def outputs(self):
        return None

    def fetch(self, params, offset=-1, count=-1):
        user_name = params[0]["user_name"].strip()
        from_ts = int(params[0]["from_ts"])
        to_ts = int(params[0]["to_ts"])
        threshold = int(params[0]["threshold"])

        MAX_TIME_RANGE = 7 * 24 * 60 * 60
        if to_ts - from_ts >= MAX_TIME_RANGE:
            to_ts = from_ts + MAX_TIME_RANGE

        with db.engine.connect() as conn:
            curs = conn.execute(text('SELECT id FROM "user" WHERE musicbrainz_id = :user_name'), user_name=user_name)
            row = curs.fetchone()
            if row:
                user_id = row["id"]
            else:
                return [
                    {
                        "type": "markup",
                        "data": f"User {user_name} not found"
                    }
                ]

        query = """
            WITH listens AS (
                 SELECT listened_at
                      , COALESCE(artist_credit_name, data->'track_metadata'->>'artist_name') AS artist_name
                      , COALESCE(recording_name, track_name) AS track_name
                      , COALESCE(recording_mbid::TEXT, data->'track_metadata'->'additional_info'->>'recording_mbid') AS recording_mbid
                      , COALESCE(
                            mbc.recording_data->>'length'::INT
                          , data->'track_metadata'->'additional_info'->>'duration'::INT
                          , (data->'track_metadata'->'additional_info'->>'duration_ms'::INT / 1000)::INT
                          , 180 -- default track length to 3 minutes
                        ) AS duration
                   FROM listen
              LEFT JOIN mbid_mapping
                     ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = recording_msid
              LEFT JOIN mbid_mapping_metadata
                  USING (recording_mbid)
              LEFT JOIN mapping.mb_metadata_cache mbc
                     ON mbc.recording_mbid = COALESCE(recording_mbid::TEXT, data->'track_metadata'->'additional_info'->>'recording_mbid')::uuid
                  WHERE listened_at > :from_ts
                    AND listened_at <= :to_ts
                    AND user_id = :user_id
               ORDER BY listened_at
            ), ordered AS (
                SELECT listened_at
                     , duration
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM listens
                WINDOW w AS (ORDER BY listened_at)
            ), sessions AS (
                SELECT listened_at
                     , duration
                     , difference
                     , COUNT(*) FILTER ( WHERE difference > :threshold ) OVER (ORDER BY listened_at) AS session_id
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM ordered
            )
                SELECT session_id
                     , jsonb_agg(
                            jsonb_build_object(
                                'listened_at', listened_at
                              , 'duration', duration  
                              , 'difference', difference
                              , 'artist_name', artist_name
                              , 'track_name', track_name
                              , 'recording_mbid', recording_mbid
                            )
                       ) AS data
                  FROM sessions
              GROUP BY session_id
        """
        results = []
        with timescale.engine.connect() as conn:
            curs = conn.execute(text(query), user_id=user_id, from_ts=from_ts, to_ts=to_ts, threshold=threshold)
            for row in curs.fetchall():
                results.append({
                    "type": "markup",
                    "data": Markup(f"<p><b>Session Number: {row['session_id']}</b></p>")
                })
                results.append({
                    "type": "dataset",
                    "columns": ["listened_at", "difference", "artist_name", "track_name", "recording_mbid"],
                    "data": row["data"]
                })
        return results
