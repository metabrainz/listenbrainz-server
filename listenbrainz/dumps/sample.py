import logging
import os
import subprocess
import tarfile
from csv import DictWriter
from uuid import UUID

from flask import current_app
from orjson import orjson
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2.sql import Identifier, SQL
from sqlalchemy import text

from listenbrainz.db import stats, timescale
from listenbrainz.db.popularity import to_entity_mbid
from listenbrainz.dumps.exceptions import SchemaMismatchException

logger = logging.getLogger(__name__)

SAMPLE_SCHEMA_VERSION = 8


def get_seed_artist_mbids():
    data = stats.get_sitewide_stats("artists", "all_time")
    return [
        UUID(artist["artist_mbid"]) for artist in data["data"]
        if artist["artist_mbid"] is not None
    ][:100]


def dump_query_to_jsonl(conn, query, params, fp, callback=None):
    result = conn.execute(query, params)
    for row in result.mappings().fetchall():
        if callback is not None:
            callback(row)
        fp.write(orjson.dumps(dict(row), option=orjson.OPT_APPEND_NEWLINE))


def get_popularity_data(cursor, entity: str, mbids: list[str], *, per_artist: bool, is_mlhd: bool):
    """ Retrieves popularity data for a given entity (recording or release group) from the database.

    Args:
        cursor: A database cursor to execute the query
        entity: The entity type, either "recording" or "release_group"
        mbids : A list of MusicBrainz IDs to fetch popularity data for
        per_artist: If True, retrieves artist-specific popularity data using the "top_entity" tables
        is_mlhd: If True, uses MLHD tables as data source

    Returns:
        list: A list of dictionaries containing popularity data including listen count and user count
    """
    entity_mbid = Identifier(to_entity_mbid(entity, per_artist))
    mlhd_prefix = "mlhd_" if is_mlhd else ""
    if per_artist:
        select_clause  = SQL("artist_mbid, {entity_mbid}").format(entity_mbid=entity_mbid)
        on_clause_mbid = Identifier("artist_mbid")
        table = Identifier("popularity", mlhd_prefix + "top_" + entity)
    else:
        on_clause_mbid = select_clause = entity_mbid
        table = Identifier("popularity", mlhd_prefix + entity)
    query = SQL("""
          WITH mbids (mbid) AS (
                VALUES %s
             )
        SELECT {select_clause}
             , total_listen_count
             , total_user_count
          FROM {table}
          JOIN mbids
            ON {on_clause_mbid} = mbid::UUID
    """).format(
        select_clause=select_clause,
        on_clause_mbid=on_clause_mbid,
        table=table
    )
    results = execute_values(cursor, query, [(mbid,) for mbid in mbids], fetch=True)
    return results


# TODO: Discuss how to fix the issue of recording msid for tracks existing in production but not locally
#   dump msid table and msid to mbid mapping table too?
def dump_sample_data(location: str):
    """ Creates a sample data dump containing a subset of metadata and popularity information.

    This function extracts sample data from the database, including:
    - Metadata for artists, recordings, and release groups from a seed list of top artists
    - Popularity data for recordings and release groups (both standard and MLHD versions)
    - Artist-specific popularity data for recordings

    The generated files are organized in subdirectories (metadata/ and popularity/).

    Args:
        location (str): Directory path where the sample dump will be stored
    """
    seed_artist_mbids = get_seed_artist_mbids()
    all_artist_mbids = set(seed_artist_mbids)
    rg_pop_mbids = set()
    rec_pop_mbids = set()

    def collect_artist_and_recording_mbids(row):
        all_artist_mbids.update(row["artist_mbids"])
        rec_pop_mbids.add(row["recording_mbid"])

    def collect_artist_release_group_mbids(row):
        all_artist_mbids.update(row["artist_mbids"])
        rg_pop_mbids.add(row["release_group_mbid"])

    with timescale.engine.connect() as connection, connection.begin() as transaction:
        metadata_dir = os.path.join(location, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        logging.info("Dumping release_groups_cache")
        with open(os.path.join(metadata_dir, "release_groups_cache.jsonl"), "wb") as fp:
            dump_query_to_jsonl(
                connection,
                text("SELECT * FROM mapping.mb_release_group_cache c WHERE c.artist_mbids && :artist_mbids"),
                {"artist_mbids": seed_artist_mbids},
                fp,
                collect_artist_release_group_mbids,
            )

        logging.info("Dumping recordings_cache")
        with open(os.path.join(metadata_dir, "recordings_cache.jsonl"), "wb") as fp:
            dump_query_to_jsonl(
                connection,
                text("SELECT * FROM mapping.mb_metadata_cache c WHERE c.artist_mbids && :artist_mbids"),
                {"artist_mbids": seed_artist_mbids},
                fp,
                collect_artist_and_recording_mbids,
            )

        logging.info("Dumping artists_cache")
        with open(os.path.join(metadata_dir, "artists_cache.jsonl"), "wb") as fp:
            dump_query_to_jsonl(
                connection,
                text("SELECT * FROM mapping.mb_artist_metadata_cache c WHERE c.artist_mbid = ANY(:artist_mbids)"),
                {"artist_mbids": list(all_artist_mbids)},
                fp,
            )

        ts_curs = connection.connection.cursor(cursor_factory=RealDictCursor)
        popularity_dir = os.path.join(location, "popularity")
        os.makedirs(popularity_dir, exist_ok=True)

        for is_mlhd in [True, False]:
            mlhd_prefix = "mlhd_" if is_mlhd else ""

            logging.info(f"Dumping popularity {mlhd_prefix}release_group")
            rg_pop_data = get_popularity_data(
                ts_curs, "release_group", rg_pop_mbids, per_artist=False, is_mlhd=is_mlhd
            )
            with open(os.path.join(popularity_dir, mlhd_prefix + "release_group.csv"), "w", newline="") as fp:
                writer = DictWriter(fp, fieldnames=["release_group_mbid", "total_listen_count", "total_user_count"])
                writer.writeheader()
                writer.writerows(rg_pop_data)

            logging.info(f"Dumping popularity {mlhd_prefix}recording")
            rec_pop_data = get_popularity_data(
                ts_curs, "recording", rg_pop_mbids, per_artist=False, is_mlhd=is_mlhd
            )
            with open(os.path.join(popularity_dir, mlhd_prefix + "recording.csv"), "w", newline="") as fp:
                writer = DictWriter(fp, fieldnames=["recording_mbid", "total_listen_count", "total_user_count"])
                writer.writeheader()
                writer.writerows(rec_pop_data)

            logging.info(f"Dumping popularity {mlhd_prefix}top_recording")
            rec_artist_pop_data = get_popularity_data(
                ts_curs, "recording", all_artist_mbids, per_artist=True, is_mlhd=is_mlhd
            )
            with open(os.path.join(popularity_dir, mlhd_prefix + "top_recording.csv"), "w", newline="") as fp:
                writer = DictWriter(fp, fieldnames=[
                    "artist_mbid", "recording_mbid", "total_listen_count", "total_user_count"
                ])
                writer.writeheader()
                writer.writerows(rec_artist_pop_data)

        transaction.rollback()


def import_sample_data(archive_path, threads):
    """ Import sample data dump from the specified archive into the postgres database.

    This function imports various components of the sample data dump:
    - Metadata for artists, recordings, and release groups (as JSONL files)
    - Popularity data for recordings and release groups (as CSV files)
    - Both standard and MLHD versions of popularity data

    The function verifies the schema version before importing to ensure compatibility.

    Args:
        archive_path: path to the .tar.zst archive containing the sample data dump
        threads (int): the number of threads to use while decompressing, defaults to
                        db.DUMP_DEFAULT_THREAD_COUNT

    Raises:
        SchemaMismatchException: If the schema version in the dump doesn't match SAMPLE_SCHEMA_VERSION
    """
    zstd_command = ["zstd", "--decompress", "--stdout", archive_path, f"-T{threads}"]
    zstd = subprocess.Popen(zstd_command, stdout=subprocess.PIPE)

    jsonl_file_table_map = {
        "release_groups_cache.jsonl": Identifier("mapping", "mb_release_group_cache"),
        "recordings_cache.jsonl": Identifier("mapping", "mb_metadata_cache"),
        "artists_cache.jsonl": Identifier("mapping", "mb_artist_metadata_cache"),
    }
    csv_file_table_map = {
        "mlhd_release_group.csv": Identifier("popularity", "mlhd_release_group"),
        "release_group.csv": Identifier("popularity", "release_group"),
        "mlhd_recording.csv": Identifier("popularity", "mlhd_recording"),
        "recording.csv": Identifier("popularity", "recording"),
        "mlhd_top_recording.csv": Identifier("popularity", "mlhd_top_recording"),
        "top_recording.csv": Identifier("popularity", "top_recording"),
    }

    connection = timescale.engine.raw_connection()
    try:
        cursor = connection.cursor()
        with tarfile.open(fileobj=zstd.stdout, mode="r|") as tar:
            for member in tar:
                file_name = member.name.split("/")[-1]

                if file_name == "SCHEMA_SEQUENCE":
                    # Verifying schema version
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != SAMPLE_SCHEMA_VERSION:
                        raise SchemaMismatchException("Incorrect schema version! Expected: %d, got: %d."
                                                      "Please, get the latest version of the dump."
                                                      % (SAMPLE_SCHEMA_VERSION, schema_seq))
                    else:
                        current_app.logger.info("Schema version verified.")

                elif file_name in jsonl_file_table_map:
                    table = jsonl_file_table_map[file_name]
                    query = SQL("""\
                        INSERT INTO {table}
                             SELECT *
                               FROM jsonb_populate_recordset(NULL::{table}, %s)
                    """).format(table=table)

                    current_app.logger.info("Importing data into %s table...", jsonl_file_table_map[file_name])
                    data = tar.extractfile(member)

                    chunk_size = 50
                    chunk = []
                    while True:
                        row = data.readline().decode("utf-8")
                        if not row:
                            break

                        chunk.append(row)
                        if len(chunk) == chunk_size:
                            param = f"[{','.join(chunk)}]"
                            cursor.execute(query, (param,))
                            chunk = []

                    if chunk:
                        param = f"[{",".join(chunk)}]"
                        cursor.execute(query, (param,))

                    connection.commit()
                    current_app.logger.info("Imported table %s", jsonl_file_table_map[file_name])
                elif file_name in csv_file_table_map:
                    current_app.logger.info("Importing data into %s table...", csv_file_table_map[file_name])

                    table = csv_file_table_map[file_name]
                    fp = tar.extractfile(member)
                    header = fp.readline().decode("utf-8").strip().split(",")
                    fields = SQL(",").join(map(Identifier, header))
                    query = SQL("COPY {table}({fields}) FROM STDIN WITH CSV").format(
                        table=table, fields=fields
                    )
                    cursor.copy_expert(query, fp)
                    connection.commit()

                    current_app.logger.info("Imported table %s", csv_file_table_map[file_name])

    finally:
        connection.close()
        zstd.stdout.close()
