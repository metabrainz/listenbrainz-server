"""Per-user top release groups from daily materialized listen counts."""
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import DAILY_RELEASE_GROUP_COUNTS, HOURLY_COUNTS
from listenbrainz.clickhouse.query_worker.top_entities import ranked_entities, refresh_top_entities


RELEASE_GROUP_LABELS = """
    CREATE TEMPORARY TABLE stats_labels ENGINE = Join(ANY, LEFT, release_group_id) AS
    SELECT release_group_id, toNullable(min(release_group_name)) AS title, min(artist_name) AS credit,
           any(artist_mbids) AS mbids, any(artists) AS credits, any(caa_id) AS cover_id,
           any(caa_release_mbid) AS cover_mbid
      FROM release_group_metadata GROUP BY release_group_id
"""


def _release_group_rows(client, users, start, end):
    fields = """title, if(release_group_id.1, toString(release_group_id.2), NULL) AS group_mbid,
                credit, mbids, credits, cover_id, cover_mbid"""
    tie_breakers = "title DESC, group_mbid DESC NULLS LAST, credit DESC, arrayMap(id -> toString(id), mbids) DESC"
    for user_id, records in ranked_entities(client, users, start, end, "release_group_id", fields, tie_breakers):
        data = []
        for _, listens, total, title, mbid, credit, mbids, artists, caa_id, caa_mbid in records:
            if title is None:
                raise RuntimeError("Missing release group metadata for a ranked release group")
            data.append({"release_group_name": title, "release_group_mbid": mbid, "listen_count": listens,
                         "artist_name": credit, "artist_mbids": mbids, "artists": artists if mbid else None,
                         "caa_id": caa_id, "caa_release_mbid": caa_mbid})
        yield {"user_id": user_id, "count": total, "data": data}


def release_groups(stats_ranges=None):
    # A day containing only untitled releases still advances the listen range.
    yield from refresh_top_entities("release_groups", stats_ranges, DAILY_RELEASE_GROUP_COUNTS, RELEASE_GROUP_LABELS,
                                    _release_group_rows, day_table=HOURLY_COUNTS.name)
