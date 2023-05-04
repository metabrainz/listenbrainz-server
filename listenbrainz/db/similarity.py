import time
from uuid import UUID

from psycopg2.extras import execute_values, DictCursor
from psycopg2.sql import SQL, Literal, Identifier

from listenbrainz.db import timescale


def insert(table, data, algorithm):
    """ Insert similar recordings in database """
    query = SQL("""
        INSERT INTO {table} AS sr (mbid0, mbid1, metadata)
             VALUES %s
        ON CONFLICT (mbid0, mbid1)
          DO UPDATE
                SET metadata = sr.metadata || EXCLUDED.metadata
    """).format(table=Identifier("similarity", table))
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


def start_prod_table(name, algorithm):
    """ Create the production table to store recording similarity data.

    When we start receiving the production table, we create a temporary table to store the data. Once
    the dataset has been received completely, we switch the temporary table with the production tables.
    We do not store the production dataset in the development tables because production dataset is generated
    daily, and we do not want leftovers from earlier runs to mixup the latst runs' results.

    Args:
        name: 'recording' or 'artist' dataset
        algorithm: the algorithm used to create the dataset
    """
    table = Identifier("similarity", f"{name}_prod_tmp")
    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            query = SQL("""
                DROP TABLE IF EXISTS {table}
            """).format(table=table)
            curs.execute(query)

            query = SQL("""
                CREATE TABLE {table} (mbid0 UUID NOT NULL, mbid1 UUID NOT NULL, score INT NOT NULL)
            """).format(table=table)
            curs.execute(query)

            query = SQL("""
                COMMENT ON TABLE {table} IS 'This dataset is created using the algorithm {algorithm}'
            """).format(table=table, algorithm=Literal(algorithm))
            curs.execute(query)

        conn.commit()
    finally:
        conn.close()


def end_prod_table(name, algorithm):
    """ Switch the temporary production table in production.

    Args:
        name: 'recording' or 'artist' dataset
        algorithm: the algorithm used to create the dataset
    """
    incoming_table = Identifier("similarity", f"{name}_prod_tmp")

    # add a random suffix to the index name to avoid issues while renaming
    suffix = int(time.time())

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            query = SQL("""
                CREATE UNIQUE INDEX similar_recordings_prod_uniq_idx_{suffix} ON {table} (mbid0, mbid1)
             """).format(table=incoming_table, suffix=Literal(suffix))
            curs.execute(query)

            query = SQL("""
                CREATE UNIQUE INDEX similar_recordings_prod_reverse_uniq_idx_{suffix} ON {table} (mbid1, mbid0)
             """).format(table=incoming_table, suffix=Literal(suffix))
            curs.execute(query)

            # rotate tables
            query = SQL("""
                ALTER TABLE {prod_table} RENAME TO {outgoing_table}
             """).format(prod_table=Identifier("similarity", f"{name}_prod"), outgoing_table=Identifier(f"{name}_prod_old"))
            curs.execute(query)
            query = SQL("""
                ALTER TABLE {incoming_table} RENAME TO {prod_table}
             """).format(incoming_table=incoming_table, prod_table=Identifier(f"{name}_prod"))
            curs.execute(query)
            query = SQL("""DROP TABLE {old_table}""").format(old_table=Identifier("similarity", f"{name}_prod_old"))
            curs.execute(query)

        conn.commit()
    finally:
        conn.close()

