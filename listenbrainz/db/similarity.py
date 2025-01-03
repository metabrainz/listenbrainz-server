from flask import current_app
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal, Identifier

from listenbrainz.db import timescale
from listenbrainz.db.artist import load_artists_from_mbids_with_redirects
from listenbrainz.spark.spark_dataset import DatabaseDataset


class SimilarityDataset(DatabaseDataset):

    def __init__(self, entity):
        super().__init__(f"similarity_{entity}", entity, "similarity")
        self.entity = entity

    def get_table(self):
        return "CREATE TABLE {table} (mbid0 UUID NOT NULL, mbid1 UUID NOT NULL, score INT NOT NULL)"

    def get_indices(self):
        return [
            f"CREATE UNIQUE INDEX similar_{self.entity}s_uniq_idx_{{suffix}} ON {{table}} (mbid0, mbid1)",
            f"CREATE UNIQUE INDEX similar_{self.entity}s_reverse_uniq_idx_{{suffix}} ON {{table}} (mbid1, mbid0)"
        ]

    def get_inserts(self, message):
        query = "INSERT INTO {table} (mbid0, mbid1, score) VALUES %s"
        values = [(x["mbid0"], x["mbid1"], x["score"]) for x in message["data"]]
        return query, None, values

    def run_post_processing(self, cursor, message):
        query = SQL("COMMENT ON TABLE {table} IS {comment}").format(
            table=self._get_table_name(),
            comment=Literal(f"This dataset is created using the algorithm {message['algorithm']}")
        )
        cursor.execute(query)


SimilarRecordingsDataset = SimilarityDataset("recording")
SimilarArtistsDataset = SimilarityDataset("artist")


def insert(table, data, algorithm):
    """ Insert similar recordings in database """
    query = SQL("""
        INSERT INTO {table} AS sr (mbid0, mbid1, metadata)
             VALUES %s
        ON CONFLICT (mbid0, mbid1)
          DO UPDATE
                SET metadata = sr.metadata || EXCLUDED.metadata
    """).format(table=Identifier("similarity", f"{table}_dev"))
    values = [(x["mbid0"], x["mbid1"], x["score"]) for x in data]
    template = SQL("(%s, %s, jsonb_build_object({algorithm}, %s))").format(algorithm=Literal(algorithm))

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            execute_values(curs, query, values, template)
        conn.commit()
    finally:
        conn.close()


def get(curs, table, mbids, algorithm, count):
    """ Fetch at most `count` number of similar recordings/artists for each mbid in the given list using
     the given algorithm.

    Returns a tuple of (list of similar mbids founds, an index of similarity scores, an index to map back
     similar mbids to the reference mbid in the input mbids)
    """
    query = SQL("""
        WITH mbids(mbid) AS (
            VALUES %s
        ), intermediate AS (
            SELECT mbid::UUID
                 , CASE WHEN mbid0 = mbid THEN mbid1 ELSE mbid0 END AS similar_mbid
                 , jsonb_object_field(metadata, {algorithm})::integer AS score
              FROM {table}
              JOIN mbids
                ON TRUE
             WHERE (mbid0 = mbid::UUID OR mbid1 = mbid::UUID)
               AND metadata ? {algorithm}
        ), ordered AS (
            SELECT mbid
                 , similar_mbid
                 , score
                 , row_number() over (PARTITION BY mbid ORDER BY score DESC) AS rnum
              FROM intermediate
        )   SELECT mbid::TEXT
                 , similar_mbid::TEXT
                 , score
              FROM ordered
             WHERE rnum <= {count}
    """).format(table=Identifier("similarity", table), algorithm=Literal(algorithm), count=Literal(count))

    results = execute_values(curs, query, [(mbid,) for mbid in mbids], "(%s::UUID)", fetch=True)

    similar_mbid_index = {}
    score_index = {}
    mbids = []
    for row in results:
        similar_mbid = row["similar_mbid"]
        similar_mbid_index[similar_mbid] = row["mbid"]
        score_index[similar_mbid] = row["score"]
        mbids.append(similar_mbid)
    return mbids, score_index, similar_mbid_index


def get_artists(mb_curs, ts_curs, mbids, algorithm, count):
    """ For the given artist mbids, fetch at most `count` number of similar artists using the given algorithm
        along with their metadata. """
    similar_mbids, score_idx, mbid_idx = get(ts_curs, "artist_credit_mbids_dev", mbids, algorithm, count)
    if not similar_mbids:
        return []

    metadata = load_artists_from_mbids_with_redirects(mb_curs, similar_mbids)
    for item in metadata:
        item["score"] = score_idx.get(item["original_artist_mbid"])
        item["reference_mbid"] = mbid_idx.get(item["artist_mbid"])
    return metadata
