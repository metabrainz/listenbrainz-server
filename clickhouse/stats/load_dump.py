"""Load listen dumps (Parquet files) into ClickHouse.

A full dump is inserted into a new table, stripped of the deleted listens and swapped
in for listens once completely loaded, so a failed load leaves listens untouched.

An incremental dump is inserted into its own ``load_id`` partition of raw_listens,
then copied into listens without the listens already there or deleted, which makes
reloading a dump safe and covers its overlap with the full dump before it.

Loads from FTP advance the incremental dump mark (import_state).
"""

import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from tempfile import TemporaryDirectory
from uuid import uuid4

from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from clickhouse.client import ClickHouseConnection
from clickhouse.stats.cache_manager import mark_users_for_recompute
from clickhouse.stats.deleted_listens import delete_all_deleted_listens
from clickhouse.stats.ftp import DumpType, FTPDumpDownloader
from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, get_import_state, record_imported_dump
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
RAW_LISTENS_TABLE = "raw_listens"
# A full dump is loaded into this table, then swapped in for listens.
REPLACE_LISTENS_TABLE = "listens_replace"

# Reset once a full dump is swapped in. Deletion records are kept.
REPLACE_TRUNCATE_TABLES = [
    "user_stats_cache_state",
    "stats_cache_state",
]

# Users whose loaded listens are older than their cached stats (back-filled): the
# stale user check only sees listens created after the last computation.
MARK_BACKFILLED_USERS = """
    SELECT c.user_id
    FROM user_stats_cache_state AS c FINAL
    INNER JOIN (
        SELECT user_id, min(created) AS min_created
        FROM raw_listens
        WHERE load_id = {load_id:String}
        GROUP BY user_id
    ) AS r ON c.user_id = r.user_id
    WHERE r.min_created <= c.last_computed_created
"""


# Copies one load's raw_listens into listens, skipping the listens already there,
# deleted listens (matched on `created`, so a re-submitted one is kept) and listens of
# deleted histories. The IN-sets only cover the load's users and `created` range: a
# re-delivered listen keeps its `created`. Users without a deleted history get the
# epoch from the LEFT JOIN (join_use_nulls = 0), so all their listens pass.
PROCESS_RAW_LISTENS = """
    INSERT INTO listens (listened_at, created, user_id, recording_msid)
    SELECT r.listened_at, r.created, r.user_id, r.recording_msid
    FROM raw_listens AS r
    LEFT JOIN (
        SELECT user_id, max(max_created) AS max_created
        FROM deleted_user_listen_history
        GROUP BY user_id
    ) AS duh ON r.user_id = duh.user_id
    WHERE r.load_id = {load_id:String}
      AND r.created > duh.max_created
      AND (r.user_id, r.listened_at, r.recording_msid) NOT IN (
            SELECT user_id, listened_at, recording_msid
            FROM listens
            WHERE user_id IN (SELECT DISTINCT user_id FROM raw_listens WHERE load_id = {load_id:String})
              AND created >= (SELECT min(created) FROM raw_listens WHERE load_id = {load_id:String})
              AND created <= (SELECT max(created) FROM raw_listens WHERE load_id = {load_id:String})
      )
      AND (r.user_id, r.listened_at, r.recording_msid, r.created) NOT IN (
            SELECT user_id, listened_at, recording_msid, created
            FROM deleted_listens
            WHERE user_id IN (SELECT DISTINCT user_id FROM raw_listens WHERE load_id = {load_id:String})
      )
"""


def describe_load_errors(errors: list[tuple[str, str]]) -> str:
    """Summarise the (file, error) pairs of a failed load."""
    examples = "; ".join(f"{path}: {error}" for path, error in errors[:3])
    return f"{len(errors)} parquet file(s) failed to load: {examples}"


PROCESS_SEND_RECEIVE_TIMEOUT = 7200


def create_client(connection: ClickHouseConnection, send_receive_timeout: int = 300) -> Client:
    return connection.connect(
        compress=False,
        form_encode_query_params=True,
        session_id=f"listenbrainz_load_dump_{uuid4().hex}",
        settings={"async_insert": 1, "wait_for_async_insert": 1},
        send_receive_timeout=send_receive_timeout,
    )


def _to_string_array(column) -> pa.Array:
    if isinstance(column, pa.ChunkedArray):
        column = column.combine_chunks()
    if not (pa.types.is_string(column.type) or pa.types.is_large_string(column.type)):
        column = pc.cast(column, pa.string())
    return pc.fill_null(column, "")


def _to_uint32_array(column) -> pa.Array:
    if isinstance(column, pa.ChunkedArray):
        column = column.combine_chunks()
    if pa.types.is_floating(column.type):
        column = pc.if_else(pc.is_nan(column), pa.scalar(None, type=column.type), column)
    column = pc.fill_null(column, 0)
    return pc.cast(column, pa.uint32())


def build_listens_arrow_table(table: pa.Table) -> pa.Table:
    """Normalize a Spark dump batch into the listens table schema."""
    return pa.table({
        "listened_at": table["listened_at"],
        "created": table["created"],
        "user_id": _to_uint32_array(table["user_id"]),
        "recording_msid": _to_string_array(table["recording_msid"]),
    })


def build_raw_listens_arrow_table(table: pa.Table, load_id: str) -> pa.Table:
    """Normalize a Spark dump batch into the raw listens table schema."""
    listens = build_listens_arrow_table(table)
    return listens.add_column(0, "load_id", pa.array([load_id] * table.num_rows, type=pa.string()))


def process_raw_listens(client: Client, load_id: str) -> None:
    """Copy one load's raw_listens into listens, skipping existing and deleted listens."""
    client.command(PROCESS_RAW_LISTENS, parameters={"load_id": load_id}, settings={"async_insert": 0})


def drop_raw_listens_partition(client: Client, load_id: str) -> None:
    """Drop the staging partition of a load (no-op if it does not exist)."""
    client.command(
        "ALTER TABLE raw_listens DROP PARTITION {load_id:String}",
        parameters={"load_id": load_id},
    )


def drop_replace_listens_table(client: Client) -> None:
    client.command(f"DROP TABLE IF EXISTS {REPLACE_LISTENS_TABLE} SETTINGS max_table_size_to_drop = 0")


def create_replace_listens_table(client: Client) -> None:
    """Create an empty table for a full dump, dropping a leftover of a failed load."""
    drop_replace_listens_table(client)
    client.command(f"CREATE TABLE {REPLACE_LISTENS_TABLE} AS {LISTENS_TABLE}")


def swap_in_replaced_listens(client: Client) -> None:
    """Strip the loaded full dump of deleted listens, make it listens and reset the cache state."""
    removed = delete_all_deleted_listens(client, REPLACE_LISTENS_TABLE)
    logger.info("Removed %s deleted listens from the full dump", f"{removed:,}")
    client.command(f"EXCHANGE TABLES {REPLACE_LISTENS_TABLE} AND {LISTENS_TABLE}")
    for table in REPLACE_TRUNCATE_TABLES:
        logger.info("Truncating %s", table)
        client.command(f"TRUNCATE TABLE IF EXISTS {table}")


def mark_backfilled_users(client: Client, load_id: str) -> None:
    """Force a recompute of users whose loaded listens are older than their cached stats."""
    mark_users_for_recompute(client, MARK_BACKFILLED_USERS, {"load_id": load_id})


def _load_parquet_file(
    file_path: Path,
    table: str,
    to_arrow: Callable[[pa.Table], pa.Table],
    connection: ClickHouseConnection,
    batch_size: int = 200_000,
) -> int:
    """Insert one Parquet file into ``table``; returns its row count."""
    client = create_client(connection)
    try:
        parquet_file = pq.ParquetFile(file_path)
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            client.insert_arrow(table=table, arrow_table=to_arrow(pa.Table.from_batches([batch])))
        return parquet_file.metadata.num_rows
    finally:
        client.close()


def find_parquet_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.parquet"))


def _insert_parquet_files(
    parquet_files: list[Path],
    table: str,
    to_arrow: Callable[[pa.Table], pa.Table],
    connection: ClickHouseConnection,
    workers: int,
) -> dict:
    """Insert the files in parallel; returns 'total_inserted', 'files_completed' and 'errors'."""
    start_time = time.time()
    total_inserted, files_completed = 0, 0
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_load_parquet_file, f, table, to_arrow, connection): f for f in parquet_files}
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                total_inserted += future.result()
                files_completed += 1
                rate = total_inserted / max(time.time() - start_time, 1e-9)
                logger.info(
                    "[%d/%d] %s rows | %s rows/sec",
                    files_completed, len(parquet_files), f"{total_inserted:,}", f"{rate:,.0f}",
                )
            except Exception as e:
                errors.append((str(file_path), str(e)))
                logger.error("Error loading %s: %s", file_path, e)
    logger.info("Inserted %s rows into %s in %.1fs", f"{total_inserted:,}", table, time.time() - start_time)
    return {"total_inserted": total_inserted, "files_completed": files_completed, "errors": errors}


def _load_full_dump(parquet_files, connection, workers, client) -> dict:
    create_replace_listens_table(client)
    try:
        result = _insert_parquet_files(parquet_files, REPLACE_LISTENS_TABLE, build_listens_arrow_table, connection, workers)
        if not result["errors"]:
            swap_in_replaced_listens(client)
    finally:
        # on success it holds the previous listens
        drop_replace_listens_table(client)
    return result


def _load_incremental_dump(parquet_files, connection, workers, client) -> dict:
    load_id = uuid4().hex
    result = _insert_parquet_files(
        parquet_files, RAW_LISTENS_TABLE, lambda table: build_raw_listens_arrow_table(table, load_id),
        connection, workers,
    )
    result["load_id"] = load_id
    if result["errors"]:
        # Keep the partition for inspection; a retry uses a new load_id.
        logger.error("Skipping processing of load %s because %d file(s) failed", load_id, len(result["errors"]))
        return result

    before = client.query("SELECT count() FROM listens").first_row[0]
    process_raw_listens(client, load_id)
    after = client.query("SELECT count() FROM listens").first_row[0]
    logger.info("Added %s new listens (%s in the dump)", f"{after - before:,}", f"{result['total_inserted']:,}")
    mark_backfilled_users(client, load_id)
    drop_raw_listens_partition(client, load_id)
    return result


def load_dump(
    directory: str,
    connection: ClickHouseConnection,
    dump_type: DumpType = DumpType.INCREMENTAL,
    workers: int = 4,
) -> dict:
    """Load the Parquet files of a dump in ``directory``; a full dump replaces listens.

    Returns 'total_inserted', 'files_completed', 'elapsed', 'errors' and, for an
    incremental dump, the 'load_id' of its raw_listens partition.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    start_time = time.time()
    parquet_files = find_parquet_files(dir_path)
    if not parquet_files:
        logger.info("No parquet files found in %s", directory)
        return {"total_inserted": 0, "files_completed": 0, "elapsed": 0, "errors": []}

    logger.info("Loading %s dump: %d parquet files with %d workers", dump_type.value, len(parquet_files), workers)
    client = create_client(connection, send_receive_timeout=PROCESS_SEND_RECEIVE_TIMEOUT)
    try:
        ensure_stats_schema(client)
        load = _load_full_dump if dump_type == DumpType.FULL else _load_incremental_dump
        result = load(parquet_files, connection, workers, client)
    finally:
        client.close()

    for path, error in result["errors"][:10]:
        logger.error("  %s: %s", path, error)
    result["elapsed"] = time.time() - start_time
    logger.info("Completed in %.1fs", result["elapsed"])
    return result


def _extract_archive(archive_path: Path, extract_dir: Path) -> Path:
    """Extract a .tar / .tar.gz / .tar.zst archive; returns the directory holding its files."""
    name = archive_path.name
    if name.endswith(".tar.zst"):
        cmd = ["tar", "--use-compress-program=zstd", "-xf", str(archive_path), "-C", str(extract_dir)]
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        cmd = ["tar", "-xzf", str(archive_path), "-C", str(extract_dir)]
    elif name.endswith(".tar"):
        cmd = ["tar", "-xf", str(archive_path), "-C", str(extract_dir)]
    else:
        raise ValueError(f"Unsupported archive format: {name}")

    logger.info("Extracting %s...", archive_path.name)
    subprocess.run(cmd, check=True)

    # the archive's top directory, if it has one
    subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
    return subdirs[0] if subdirs else extract_dir


def _load_archive(
    archive_path: Path,
    dump_id: int,
    dump_type: DumpType,
    connection: ClickHouseConnection,
    workers: int,
) -> dict:
    """Extract and load a dump archive, advancing the incremental dump mark if it loaded cleanly."""
    with TemporaryDirectory(prefix="clickhouse_dump_extract_") as extract_dir:
        parquet_dir = _extract_archive(archive_path, Path(extract_dir))
        logger.info("Extracted to %s", parquet_dir)
        result = load_dump(str(parquet_dir), connection, dump_type, workers)

    result["dump_id"] = dump_id
    if not result["errors"]:
        client = create_client(connection)
        try:
            record_imported_dump(client, dump_id, dump_type)
        finally:
            client.close()
    return result


def load_from_ftp(
    dump_type: DumpType,
    connection: ClickHouseConnection,
    *,
    workers: int = 4,
    dump_id: int | None = None,
) -> dict:
    """Download dump ``dump_id`` (latest if None) from FTP and load it."""
    with TemporaryDirectory(prefix="clickhouse_dump_download_") as download_dir:
        with FTPDumpDownloader() as downloader:
            archive_path, loaded_dump_id = downloader.download_dump_archive(dump_type, download_dir, dump_id)
        logger.info("Downloaded %s dump %d: %s", dump_type.value, loaded_dump_id, Path(archive_path).name)
        return _load_archive(Path(archive_path), loaded_dump_id, dump_type, connection, workers)


def import_missing_incremental_dumps(
    connection: ClickHouseConnection,
    *,
    workers: int = 4,
    max_dumps: int | None = None,
) -> dict:
    """Load the incremental dumps on FTP newer than the incremental dump mark, oldest first.

    Stops at the first failure, so that dump is retried next run rather than skipped.
    ``max_dumps`` limits how many are loaded in this run.

    Returns 'imported', 'pending', 'available', 'errors' and 'elapsed'.
    """
    start_time = time.time()

    client = create_client(connection)
    try:
        ensure_stats_schema(client)
        last_id = get_import_state(client, INCREMENTAL_DUMP_STATE)
    finally:
        client.close()

    with FTPDumpDownloader() as downloader:
        available = downloader.list_dump_ids(DumpType.INCREMENTAL)

    if last_id:
        missing = [dump for dump in available if dump[0] > last_id]
    else:
        # Nothing loaded yet, so nothing to catch up from: load only the newest
        # incremental, as the Spark pipeline does.
        logger.warning(
            "No dump import recorded; loading only the latest incremental dump. "
            "Run a full dump import to enable catch-up."
        )
        missing = available[-1:]

    pending = len(missing)
    if max_dumps is not None:
        missing = missing[:max_dumps]

    logger.info(
        "%d incremental dump(s) on FTP, %d not loaded yet, loading %d now",
        len(available), pending, len(missing),
    )

    imported, errors = [], []
    for missing_dump_id, dump_dir_name in missing:
        logger.info("Loading incremental dump %d (%s)", missing_dump_id, dump_dir_name)
        try:
            result = load_from_ftp(
                DumpType.INCREMENTAL, connection,
                workers=workers, dump_id=missing_dump_id,
            )
        except Exception as e:
            logger.error("Error loading incremental dump %d: %s", missing_dump_id, e, exc_info=True)
            errors.append((missing_dump_id, str(e)))
            break

        if result["errors"]:
            errors.append((missing_dump_id, describe_load_errors(result["errors"])))
            break

        imported.append(result)

    return {
        "imported": imported,
        "pending": pending - len(imported),
        "available": len(available),
        "errors": errors,
        "elapsed": time.time() - start_time,
    }
