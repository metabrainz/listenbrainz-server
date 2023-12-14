from flask import current_app
from psycopg2.extras import DictCursor, execute_values
from psycopg2.sql import SQL, Identifier
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.spark.spark_dataset import DatabaseDataset

import psycopg2


class PopularityDataset(DatabaseDataset):
    """ Dataset class for artists, recordings and releases with popularity info (listen count and unique listener count)
     from MLHD data """

    def __init__(self, entity):
        super().__init__(f"mlhd_popularity_{entity}", entity, "popularity")
        self.entity = entity
        self.entity_mbid = f"{entity}_mbid"

    def get_table(self):
        return f"""
            CREATE TABLE {{table}} (
                {self.entity_mbid}      UUID NOT NULL,
                total_listen_count      INTEGER NOT NULL,
                total_user_count        INTEGER NOT NULL
            )
        """

    def get_inserts(self, message):
        query = f"INSERT INTO {{table}} ({self.entity_mbid}, total_listen_count, total_user_count) VALUES %s"
        values = [(r[self.entity_mbid], r["total_listen_count"], r["total_user_count"]) for r in message["data"]]
        return query, None, values


class PopularityTopDataset(DatabaseDataset):
    """ Dataset class for all recordings and releases with popularity info (total listen count and unique listener
     count) for each artist in MLHD data. """
    def __init__(self, entity):
        super().__init__(f"mlhd_popularity_top_{entity}", f"top_{entity}", "popularity")
        self.entity = entity
        self.entity_mbid = f"{entity}_mbid"

    def get_table(self):
        return f"""
            CREATE TABLE {{table}} (
                artist_mbid             UUID NOT NULL,
                {self.entity_mbid}      UUID NOT NULL,
                total_listen_count      INTEGER NOT NULL,
                total_user_count        INTEGER NOT NULL
            )
        """

    def get_inserts(self, message):
        query = f"INSERT INTO {{table}} (artist_mbid, {self.entity_mbid}, total_listen_count, total_user_count) VALUES %s"
        values = [
            (r["artist_mbid"], r[self.entity_mbid], r["total_listen_count"], r["total_user_count"])
            for r in message["data"]
        ]
        return query, None, values


RecordingPopularityDataset = PopularityDataset("recording")
ArtistPopularityDataset = PopularityDataset("artist")
ReleasePopularityDataset = PopularityDataset("release")
ReleaseGroupPopularityDataset = PopularityDataset("release_group")
TopRecordingPopularityDataset = PopularityTopDataset("recording")
TopReleasePopularityDataset = PopularityTopDataset("release")
TopReleaseGroupPopularityDataset = PopularityTopDataset("release_group")


def get_top_entity_for_entity(entity, artist_mbid, popularity_entity="recording"):
    """ Get the top recordings or releases for a given artist mbid """
    if entity == "recording":
        entity_mbid = "recording_mbid"
    elif entity == "release-group":
        entity_mbid = "release_group_mbid"
        entity = "release_group"
        popularity_entity = "release_group"
    else:
        entity_mbid = "release_mbid"
    query = """
        SELECT """ + entity_mbid + """::TEXT
             , total_listen_count
             , total_user_count
          FROM popularity.top_""" + popularity_entity + """
         WHERE artist_mbid = :artist_mbid
      ORDER BY total_listen_count DESC
    """
    with timescale.engine.begin() as connection:
        results = connection.execute(text(query), {"artist_mbid": artist_mbid})
        return results.mappings().all()


def get_counts(entity, mbids):
    """ Get the total listen and user counts for a given entity and list of mbids """
    if entity == "recording":
        entity_mbid = "recording_mbid"
    elif entity == "release_group":
        entity_mbid = "release_group_mbid"
    elif entity == "release":
        entity_mbid = "release_mbid"
    else:
        return []

    query = SQL("""
          WITH mbids (mbid) AS (VALUES %s)
        SELECT mbid
             , total_listen_count
             , total_user_count
          FROM {table}
          JOIN mbids
            ON {entity_mbid} = mbid::UUID
    """).format(entity_mbid=Identifier(entity_mbid), table=Identifier("popularity", entity))
    with timescale.engine.begin() as connection:
        ts_curs = connection.connection.cursor()
        results = execute_values(ts_curs, query, [(mbid,) for mbid in mbids], fetch=True)
        index = {row[0]: (row[1], row[2]) for row in results}

    entity_data = []
    for mbid in mbids:
        total_listen_count, total_user_count = index.get(mbid, (None, None))
        entity_data.append({
            entity_mbid: mbid,
            "total_listen_count": total_listen_count,
            "total_user_count": total_user_count
        })
    return entity_data
