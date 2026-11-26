"""Per-user top recordings from signed daily counts and MusicBrainz metadata."""
from contextlib import ExitStack, contextmanager
from itertools import groupby
from operator import itemgetter

from more_itertools import chunked

from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import DAILY_RECORDING_COUNTS, RECORDING_METADATA
from listenbrainz.clickhouse.query_worker.metadata_tables import RECORDING_ARTIST_CACHE, RELEASE_METADATA_CACHE
from listenbrainz.clickhouse.query_worker.top_entities import refresh_top_entities, temporary_table


@contextmanager
def _recording_metadata(client):
    with ExitStack() as stack:
        stack.enter_context(temporary_table(client, "stats_recording_metadata",
                                            f"CLONE AS {RECORDING_METADATA.name} ENGINE = {RECORDING_METADATA.engine}"))
        for table in (RECORDING_ARTIST_CACHE, RELEASE_METADATA_CACHE):
            if client.command(f"EXISTS TABLE {table.name}"):
                definition = f"CLONE AS {table.name} ENGINE = MergeTree ORDER BY {table.order_by}"
            else:
                definition = f"({table.columns}) ENGINE = Memory"
            stack.enter_context(temporary_table(client, f"stats_{table.name}", definition))
        yield


TOP_RECORDINGS = """
    ENGINE = Memory AS
    WITH counts AS (
        SELECT user_id, recording_id, release_group_id, sum(listen_count) AS listens
          FROM stats_snapshot
         WHERE user_id BETWEEN {first:UInt32} AND {last:UInt32} AND day >= {start:Date} AND day < {end:Date}
         GROUP BY user_id, recording_id, release_group_id
        HAVING listens > 0
    ), spellings AS (
        SELECT user_id, track_name, recording_mbid, artist_name, artist_mbids, release_name, release_mbid, listens
          FROM counts ANY LEFT JOIN (
              SELECT *, true AS matched FROM stats_recording_metadata
               WHERE recording_id IN (SELECT recording_id FROM counts)
          ) AS metadata USING (recording_id)
         WHERE NOT throwIf(matched = 0, 'Missing metadata for a counted recording')
    ), recordings AS (
        WITH min((track_name, artist_name, release_name)) AS names
        SELECT user_id, names.1 AS title, recording_mbid, names.2 AS credit, artist_mbids,
               nullIf(names.3, '') AS album, release_mbid, sum(listens) AS plays
          FROM spellings
         GROUP BY user_id, lowerUTF8(track_name), recording_mbid, lowerUTF8(artist_name), artist_mbids,
                  lowerUTF8(release_name), release_mbid
    )
    SELECT *, count() OVER (PARTITION BY user_id) AS total,
           row_number() OVER (PARTITION BY user_id ORDER BY plays DESC, title DESC,
               toString(recording_mbid) DESC NULLS LAST, credit DESC, arrayMap(id -> toString(id), artist_mbids) DESC,
               album DESC NULLS LAST, toString(release_mbid) DESC NULLS LAST) AS position
      FROM recordings
   QUALIFY position <= 1000
"""

# Limit both indexed cache lookups to the MBIDs in this batch's top recordings.
RECORDING_ROWS = """
    SELECT user_id, total, plays, title, recording_mbid, credit, artist_mbids, album, release_mbid,
           matched_credit, artists, caa_id, caa_release_mbid
      FROM top_recordings
      ANY LEFT JOIN (
          SELECT recording_mbid, true AS matched_credit, artists FROM stats_recording_artist_cache
           WHERE recording_mbid IN (SELECT recording_mbid FROM top_recordings)
      ) AS rec USING (recording_mbid)
      ANY LEFT JOIN (
          SELECT release_mbid, caa_id, caa_release_mbid FROM stats_release_metadata_cache
           WHERE release_mbid IN (SELECT release_mbid FROM top_recordings)
      ) AS rel USING (release_mbid)
     ORDER BY user_id, position
"""


def _recording_rows(client, users, start, end):
    for batch in chunked(users, 100):
        params = {"first": batch[0][0], "last": batch[-1][0], "start": start.date(), "end": end.date()}
        with temporary_table(client, "top_recordings", TOP_RECORDINGS, params), \
                client.query_rows_stream(RECORDING_ROWS, query_formats={"UUID": "string"}) as rows:
            for user_id, records in groupby(rows, itemgetter(0)):
                data = []
                invalid = 0
                for (_, total, plays, title, mbid, credit, mbids, album, release,
                     matched, artists, caa, cover) in records:
                    if not credit:  # Spark drops ranked entries that fail RecordingRecord's artist name check.
                        invalid += 1
                        continue
                    data.append({"listen_count": plays, "track_name": title, "recording_mbid": mbid,
                                 "artist_name": credit, "artist_mbids": mbids, "release_name": album,
                                 "release_mbid": release, "artists": artists if matched else None,
                                 "caa_id": caa, "caa_release_mbid": cover})
                yield {"user_id": user_id, "count": total - invalid, "data": data}


def recordings(stats_ranges=None):
    yield from refresh_top_entities("recordings", stats_ranges, DAILY_RECORDING_COUNTS, _recording_metadata,
                                    _recording_rows)
