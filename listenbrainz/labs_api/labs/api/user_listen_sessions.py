from datasethoster import Query
from markupsafe import Markup
from sqlalchemy import text

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
        query = """
            WITH listens AS (
                 SELECT listened_at
                      , COALESCE(artist_credit_name, data->'track_metadata'->>'artist_name') AS artist_name
                      , COALESCE(recording_name, data->'track_metadata'->>'track_name') AS track_name
                      , COALESCE(recording_mbid::TEXT, data->'track_metadata'->'additional_info'->>'recording_mbid') AS recording_mbid
                   FROM listen l
              LEFT JOIN mbid_mapping mm
                     ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = mm.recording_msid
              LEFT JOIN mbid_mapping_metadata m
                  USING (recording_mbid)
                  WHERE listened_at > :from_ts::INT
                    AND listened_at <= :to_ts::INT
                    AND user_id = :user_id
               ORDER BY listened_at
            ), ordered AS (
                SELECT listened_at
                     , listened_at - LAG(listened_at, 1) OVER (ORDER BY listened_at) AS difference
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM listens
            ), sessions AS (
                SELECT listened_at
                     , difference
                     , COUNT(*) FILTER ( WHERE difference > :threshold::INT ) OVER (ORDER BY listened_at) AS session_id
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM ordered
            )
                SELECT session_id
                     , jsonb_agg(
                            jsonb_build_object(
                                'listened_at', listened_at
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
            curs = conn.execute(text(query), **params[0])
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
