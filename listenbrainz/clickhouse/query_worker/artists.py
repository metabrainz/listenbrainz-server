"""Per-user top artists from daily materialized listen counts."""
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import DAILY_ARTIST_COUNTS
from listenbrainz.clickhouse.query_worker.top_entities import ranked_entities, refresh_top_entities


ARTIST_LABELS = """
    CREATE TEMPORARY TABLE stats_labels ENGINE = Join(ANY, LEFT, artist_id) AS
    SELECT artist_id, toNullable(min(display_name)) AS artist_name, min(artist_mbid) AS mbid
      FROM artist_metadata GROUP BY artist_id
"""


def _artist_rows(client, users, start, end):
    for user_id, records in ranked_entities(client, users, start, end, "artist_id",
                                            "artist_name, nullIf(mbid, '') AS result_mbid",
                                            "artist_name DESC, result_mbid DESC NULLS LAST"):
        data = []
        invalid = 0
        for _, listens, total, name, mbid in records:
            if name is None:
                raise RuntimeError("Missing artist metadata for a ranked artist")
            if name:
                data.append({"artist_name": name, "artist_mbid": mbid, "listen_count": listens})
            else:
                invalid += 1
        yield {"user_id": user_id, "count": total - invalid, "data": data}


def artists(stats_ranges=None):
    yield from refresh_top_entities("artists", stats_ranges, DAILY_ARTIST_COUNTS, ARTIST_LABELS, _artist_rows)
