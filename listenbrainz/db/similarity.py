from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal, Identifier, Composable

from listenbrainz.db import timescale
from listenbrainz.db.artist import load_artists_from_mbids_with_redirects
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects
from listenbrainz.spark.spark_dataset import DatabaseDataset, SparkDataset


class SimilarityProdDataset(DatabaseDataset):

    def __init__(self, entity, is_mlhd):
        if is_mlhd:
            name = f"mlhd_similarity_{entity}"
            table_name = f"mlhd_{entity}"
            index_prefix = f"mlhd_sim"
        else:
            name = f"listens_similarity_{entity}"
            table_name = entity
            index_prefix = f"sim"
        super().__init__(name, table_name, "similarity")
        self.is_mlhd = is_mlhd
        self.entity = entity
        self.index_prefix = index_prefix

    def get_table(self):
        return "CREATE TABLE {table} (mbid0 UUID NOT NULL, mbid1 UUID NOT NULL, score INT NOT NULL)"

    def get_indices(self):
        return [
            f"CREATE UNIQUE INDEX {self.index_prefix}_{self.entity}s_uniq_idx_{{suffix}} ON {{table}} (mbid0, mbid1)",
            f"CREATE UNIQUE INDEX {self.index_prefix}_{self.entity}s_reverse_uniq_idx_{{suffix}} ON {{table}} (mbid1, mbid0)"
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


class SimilarityDevDataset(DatabaseDataset):

    def __init__(self, entity, is_mlhd):
        if is_mlhd:
            name = f"mlhd_similarity_{entity}_dev"
            table_name = f"mlhd_{entity}_dev"
            index_prefix = "mlhd_sim_dev"
        else:
            name = f"listens_similarity_{entity}_dev"
            table_name = f"{entity}_dev"
            index_prefix = "sim_dev"
        super().__init__(name, table_name, "similarity")
        self.is_mlhd = is_mlhd
        self.entity = entity
        self.index_prefix = index_prefix

    def get_table(self):
        return "CREATE TABLE IF NOT EXISTS {table} (mbid0 UUID NOT NULL, mbid1 UUID NOT NULL, metadata JSONB NOT NULL)"

    def create_table(self, cursor):
        table = self._get_table_name()
        query = self.get_table()
        if not isinstance(query, Composable):
            query = SQL(query).format(table=table)
        cursor.execute(query)

    def get_indices(self):
        return [
            f"CREATE UNIQUE INDEX IF NOT EXISTS {self.index_prefix}_{self.entity}s_uniq_idx ON {{table}} (mbid0, mbid1)",
            f"CREATE UNIQUE INDEX IF NOT EXISTS {self.index_prefix}_{self.entity}s_reverse_uniq_idx ON {{table}} (mbid1, mbid0)",
            f"CREATE INDEX IF NOT EXISTS {self.index_prefix}_{self.entity}s_algorithm_idx ON {{table}} USING GIN (metadata jsonb_path_ops)"
        ]

    def create_indices(self, cursor):
        table = self._get_table_name()
        for index in self.get_indices():
            query = SQL(index).format(table=table)
            cursor.execute(query)

    def rotate_tables(self, cursor):
        pass

    def run_post_processing(self, cursor, message):
        cursor.execute(SQL("VACUUM ANALYZE {table}").format(table=self._get_table_name()))

    def get_inserts(self, message):
        algorithm = message["algorithm"]
        data = message["data"]
        query = """
            INSERT INTO {table} AS sr (mbid0, mbid1, metadata)
                 VALUES %s
            ON CONFLICT (mbid0, mbid1)
              DO UPDATE
                    SET metadata = sr.metadata || EXCLUDED.metadata
        """
        template = SQL("(%s, %s, jsonb_build_object({algorithm}, %s))").format(
            algorithm=Literal(algorithm)
        )
        values = [(x["mbid0"], x["mbid1"], x["score"]) for x in data]
        return query, template, values

    def handle_insert(self, message):
        query, template, values = self.get_inserts(message)
        table = self._get_table_name()
        query = SQL(query).format(table=table)

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, values, template)
            conn.commit()
        finally:
            conn.close()


class SimilarityDataset(SparkDataset):

    def __init__(self, entity, is_mlhd):
        if is_mlhd:
            name = "mlhd_similarity"
        else:
            name = "listens_similarity"
        super().__init__(f"{name}_{entity}")
        self.dev_dataset = SimilarityDevDataset(entity, is_mlhd)
        self.prod_dataset = SimilarityProdDataset(entity, is_mlhd)

    def choose_dataset(self, message):
        return self.prod_dataset if message["is_production_dataset"] else self.dev_dataset

    def handle_start(self, message):
        dataset = self.choose_dataset(message)
        dataset.handle_start(message)

    def handle_insert(self, message):
        dataset = self.choose_dataset(message)
        dataset.handle_insert(message)

    def handle_end(self, message):
        dataset = self.choose_dataset(message)
        dataset.handle_end(message)

    def handle_shutdown(self):
        self.dev_dataset.handle_shutdown()
        self.prod_dataset.handle_shutdown()


SimilarRecordingsDataset = SimilarityDataset("recording", False)
SimilarArtistsDataset = SimilarityDataset("artist", False)
MlhdSimilarRecordingsDataset = SimilarityDataset("recording", True)


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


def get_recordings(mb_curs, ts_curs, mbids, algorithm, count):
    """ For the given recording mbids, fetch at most `count` number of similar recordings using the given algorithm
        along with their metadata. """
    similar_mbids, score_idx, mbid_idx = get(ts_curs, "recording_dev", mbids, algorithm, count)
    if not similar_mbids:
        return []

    metadata = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, similar_mbids)

    for item in metadata:
        item["score"] = score_idx.get(item["original_recording_mbid"])
        item["reference_mbid"] = mbid_idx.get(item["recording_mbid"])
    return metadata
