from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID

from datasethoster import Query, QueryOutputLine
from markupsafe import Markup
from pydantic import BaseModel
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale

SESSION_SKIP_THRESHOLD = 30
DEFAULT_TRACK_LENGTH = 180
MAX_TIME_RANGE = timedelta(days=31)


class UserListensSessionInput(BaseModel):
    user_name: str
    from_ts: datetime
    to_ts: datetime
    threshold: int


class UserListensSessionOutputItem(BaseModel):
    listened_at: str
    duration: int
    difference: Optional[int]
    skipped: Optional[int]
    artist_name: str
    track_name: str
    recording_mbid: Optional[UUID]


UserListensSessionOutput = Union[QueryOutputLine, UserListensSessionOutputItem]


class UserListensSessionQuery(Query):
    """ Display sessions of user's listens as sessions for given time period """

    def setup(self):
        pass

    def names(self):
        return "sessions-viewer", "ListenBrainz Session Viewer"

    def inputs(self):
        return UserListensSessionInput

    def introduction(self):
        return """This page allows you to view the listens of the given time period for a user distributed
         into sessions. Listens are considered to belong to same session if the time difference between any
         two consecutive listens in that set is less than a given threshold. 
         
         The difference takes into consideration the duration of the recording listened. If the duration of
         the recording is unavailable in MB and the listen metadata, it is assumed to be 180s.
        """

    def outputs(self):
        return UserListensSessionOutput

    def fetch(self, params, source, offset=-1, count=-1):
        user_name = params[0].user_name
        from_ts = params[0].from_ts
        to_ts = params[0].to_ts
        threshold = params[0].threshold

        if to_ts - from_ts >= MAX_TIME_RANGE:
            to_ts = from_ts + MAX_TIME_RANGE

        with db.engine.connect() as conn:
            curs = conn.execute(text('SELECT id FROM "user" WHERE musicbrainz_id = :user_name'), {"user_name": user_name})
            row = curs.fetchone()
            if row:
                user_id = row.id
            else:
                return [QueryOutputLine(line=Markup(f"User {user_name} not found"))]

        query = f"""
            WITH listens AS (
                 SELECT listened_at
                      , COALESCE(mbc.artist_data->>'name', l.data->>'artist_name') AS artist_name
                      , COALESCE(mbc.recording_data->>'name', l.data->>'track_name') AS track_name
                      , COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                      , make_interval(secs => COALESCE(
                            (mbc.recording_data->>'length')::INT / 1000
                          , (l.data->'additional_info'->>'duration')::INT
                          , (l.data->'additional_info'->>'duration_ms')::INT / 1000
                          , {DEFAULT_TRACK_LENGTH}
                        )) AS duration
                   FROM listen l
              LEFT JOIN mbid_mapping mm
                     ON l.recording_msid = mm.recording_msid
              LEFT JOIN mbid_manual_mapping user_mm
                     ON l.recording_msid = user_mm.recording_msid
                    AND user_mm.user_id = l.user_id 
              LEFT JOIN mbid_manual_mapping_top other_mm
                     ON l.recording_msid = other_mm.recording_msid
              LEFT JOIN mapping.mb_metadata_cache mbc
                     ON mbc.recording_mbid = COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid)
                  WHERE listened_at > :from_ts
                    AND listened_at <= :to_ts
                    AND l.user_id = :user_id
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
            ), detect_skips AS (
                SELECT listened_at
                     , duration
                     , difference
                     -- a 30s leeway to allow for difference in track length in MB and other services or any issue
                     -- in timestamping
                     , LEAD(difference, 1) OVER w < - make_interval(secs => {SESSION_SKIP_THRESHOLD}) AS skipped
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM ordered
                WINDOW w AS (ORDER BY listened_at)
            ), sessions AS (
                SELECT listened_at
                     , duration
                     , difference
                     , skipped
                     , COUNT(*) FILTER ( WHERE difference > make_interval(secs => :threshold) ) OVER w AS session_id
                     , artist_name
                     , track_name
                     , recording_mbid
                  FROM detect_skips
                WINDOW w AS (ORDER BY listened_at)
            )
                SELECT session_id
                     , jsonb_agg(
                            jsonb_build_object(
                                'listened_at', to_char(listened_at, 'YYYY-MM-DD HH24:MI:SS')
                              , 'duration', extract(epoch from duration)  
                              , 'difference', extract(epoch from difference)
                              , 'skipped', skipped
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
            curs = conn.execute(text(query), {
                "user_id": user_id,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "threshold": threshold,
            })
            for row in curs.fetchall():
                results.append(QueryOutputLine(
                    line=Markup(f"<p><b>Session Number: {row.session_id}</b></p>")
                ))
                results.extend([UserListensSessionOutputItem(**item) for item in row.data])
        return results
