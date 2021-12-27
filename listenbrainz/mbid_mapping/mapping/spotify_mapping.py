from datetime import datetime

from sqlalchemy import text

from listenbrainz.db import timescale

base_query_begin = text("""
    INSERT INTO spotify_mapping
         SELECT data->'track_metadata'->'additional_info'->>'recording_msid'::UUID
              , data->'track_metadata'->'additional_info'->>'spotify_id'
              , data->'track_metadata'->'additional_info'->>'spotify_album_id'
              , data->'track_metadata'->'additional_info'->>'spotify_artist_ids'
              , data->'track_metadata'->'additional_info'->>'spotify_album_artist_ids'
              , data->'track_metadata'->'additional_info'->>'isrc'
           FROM listen
          WHERE data->'track_metadata'->'additional_info'->>'recording_msid' IS NOT NULL
            AND data->'track_metadata'->'additional_info'->>'spotify_id' IS NOT NULL
            AND """)
initial_query = text("listened_at >= :start AND listened_at < :end")
incremental_query = text("created >= :watermark")
# spotify_id field is considered while calculating a msid, so one msid can only have
# one spotify track id associated with it. Assuming, given a spotify track id other
# spotify ids do not change all ids for a given msid will be fixed. Thus, ignoring rows
# if msid is already present in mapping is enough to avoid duplicates and not lose data.
base_query_end = text(" ON CONFLICT (recording_msid) DO NOTHING")

LISTEN_MINIMUM_TS = int(datetime(2002, 10, 1).timestamp())
CHUNK_SECONDS = 432000


# TODO: decide what to do with watermark - run for last time period or store last run timestamp somewhere
def _incremental_run(start):
    final_query = base_query_begin + incremental_query
    with timescale.engine.connect() as connection:
        connection.execute(final_query, watermark=start)


def _initial_run():
    final_query = base_query_begin + initial_query
    start = LISTEN_MINIMUM_TS
    end = int(datetime.now().timestamp())
    with timescale.engine.connect() as connection:
        while start < end:
            connection.execute(final_query, start=start, end=start + CHUNK_SECONDS)
            start += CHUNK_SECONDS
