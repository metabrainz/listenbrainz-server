"""Load listen dumps (Parquet files) into ClickHouse.

Each load inserts a dump into a staging table of its own, so a failed load leaves
listens untouched, then publishes it:

A full dump's staging table is swapped in for listens.

An incremental dump's staging table is copied into listens without the listens
already there, which makes reloading a dump safe and covers its overlap with the full
dump before it.

A dump is read from a directory of Parquet files or, as downloaded from FTP, from its
uncompressed .tar archive in place: full dumps are hundreds of GB, too big to extract.

Imports from FTP advance the incremental dump mark (import_state). Each import first
drops what imports that failed without cleaning up left behind.
"""

import logging
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from tempfile import TemporaryDirectory
from uuid import uuid4

from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.parquet as pq

from listenbrainz.clickhouse.query_worker.client import ClickHouseConnection
from listenbrainz.clickhouse.query_worker.listens.ftp import DumpType, FTPDumpDownloader
from listenbrainz.clickhouse.query_worker.listens.import_state import INCREMENTAL_DUMP_STATE, get_import_state, set_import_state
from listenbrainz.clickhouse.query_worker.listens.schema import LISTEN_COLUMN_NAMES, create_listens_table, ensure_schema
from listenbrainz.clickhouse.query_worker.utils import describe_load_errors

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
STAGING_TABLE_PREFIX = "listens_staging_"

_COLUMNS = ", ".join(LISTEN_COLUMN_NAMES)

# Insert staging listens, excluding existing keys and duplicates within staging.
MERGE_STAGED_LISTENS = f"""
    INSERT INTO listens ({_COLUMNS})
    SELECT {_COLUMNS}
    FROM {{table}}
    WHERE (user_id, listened_at, recording_msid) NOT IN (
        SELECT user_id, listened_at, recording_msid
        FROM listens
    )
    LIMIT 1 BY user_id, listened_at, recording_msid
"""


PROCESS_SEND_RECEIVE_TIMEOUT = 7200
COVERAGE_STATE = "dump_coverage_end_us"


COVERAGE_FILES = {"TIMESTAMP", "START_TIMESTAMP", "END_TIMESTAMP"}
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _read_coverage_timestamp(archive: tarfile.TarFile, member: tarfile.TarInfo) -> int:
    """A coverage timestamp of a dump, in microseconds since the epoch."""
    if not member.isfile() or member.size > 128:
        raise ValueError(f"Invalid dump metadata: {member.name}")
    value = datetime.fromisoformat(archive.extractfile(member).read().decode().strip())
    if value.tzinfo is None:
        raise ValueError(f"Dump timestamp has no timezone: {member.name}")
    # integer arithmetic: one dump's end must equal the next one's start exactly
    return (value - EPOCH) // timedelta(microseconds=1)


def dump_coverage(timestamps: dict[str, int], dump_type: DumpType) -> tuple[int, int]:
    """The (start, end) coverage of a dump in microseconds, from the timestamps of read_archive."""
    names = {"TIMESTAMP"} if dump_type == DumpType.FULL else {"START_TIMESTAMP", "END_TIMESTAMP"}
    if names - timestamps.keys():
        raise ValueError("Dump is missing coverage timestamps; import a fresh full dump")
    end = timestamps["TIMESTAMP"] if dump_type == DumpType.FULL else timestamps["END_TIMESTAMP"]
    start = end if dump_type == DumpType.FULL else timestamps["START_TIMESTAMP"]
    if not 0 < start <= end:
        raise ValueError("Invalid dump coverage interval")
    return start, end


def create_client(connection: ClickHouseConnection, send_receive_timeout: int = 300) -> Client:
    return connection.connect(
        compress="lz4",
        form_encode_query_params=True,
        send_receive_timeout=send_receive_timeout,
    )


def merge_staged_listens(client: Client, table: str) -> None:
    """Copy a staging table into listens, skipping the listens already there."""
    client.command(MERGE_STAGED_LISTENS.format(table=table))


def create_staging_table(client: Client) -> str:
    """Create a staging table private to one load, with the schema of listens."""
    table = f"{STAGING_TABLE_PREFIX}{uuid4().hex}"
    create_listens_table(client, table)
    return table


def drop_staging_table(client: Client, table: str) -> None:
    client.command(f"DROP TABLE IF EXISTS {table} SETTINGS max_table_size_to_drop = 0")


@contextmanager
def staging_table(client: Client) -> Iterator[str]:
    table = create_staging_table(client)
    try:
        yield table
    finally:
        drop_staging_table(client, table)


def drop_import_leftovers(client: Client) -> None:
    """Drop the staging tables of imports that stopped without cleaning up.
    Only call it when no other import runs: it drops their staging tables too.
    """
    leftovers = client.query(
        "SELECT name FROM system.tables WHERE database = currentDatabase() AND startsWith(name, {prefix:String})",
        parameters={"prefix": STAGING_TABLE_PREFIX},
    ).result_rows
    for (table,) in leftovers:
        logger.warning("Dropping %s, left behind by an earlier import", table)
        drop_staging_table(client, table)


def swap_in_staged_listens(client: Client, table: str) -> None:
    client.command(f"EXCHANGE TABLES {table} AND {LISTENS_TABLE}")


def count_listens(client: Client) -> int:
    return client.query(f"SELECT count() FROM {LISTENS_TABLE}").first_row[0]


@dataclass(frozen=True)
class ArchiveMember:
    """A Parquet file inside an uncompressed tar archive, read in place."""
    archive: Path
    name: str
    offset: int
    size: int

    def __str__(self):
        return f"{self.archive.name}:{self.name}"


ParquetSource = Path | ArchiveMember


@contextmanager
def _open_parquet_file(source: ParquetSource) -> Iterator[pq.ParquetFile]:
    if isinstance(source, ArchiveMember):
        with pa.memory_map(str(source.archive)) as archive:
            yield pq.ParquetFile(pa.BufferReader(archive.read_at(source.size, source.offset)))
    else:
        yield pq.ParquetFile(source)


def _load_parquet_file(
    source: ParquetSource,
    table: str,
    client: Client,
    batch_size: int = 200_000,
) -> int:
    """Insert one Parquet file into ``table``; returns its row count. ClickHouse converts
    the dump's columns (SPARK_LISTENS_SCHEMA) to those of the table on insert."""
    with _open_parquet_file(source) as parquet_file:
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=LISTEN_COLUMN_NAMES):
            client.insert_arrow(table=table, arrow_table=pa.Table.from_batches([batch]))
        return parquet_file.metadata.num_rows


def find_parquet_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.parquet"))


def read_archive(path: Path) -> tuple[list[ArchiveMember], dict[str, int]]:
    """The Parquet files of an uncompressed .tar archive and its coverage timestamps
    (see dump_coverage), in one pass over the archive.
    """
    members, timestamps = [], {}
    # "r:" only opens uncompressed archives, whose members can be read in place
    with tarfile.open(path, mode="r:") as archive:
        for member in archive:
            name = Path(member.name).name
            if member.isfile() and name.endswith(".parquet"):
                members.append(ArchiveMember(path, member.name, member.offset_data, member.size))
            elif name in COVERAGE_FILES:
                if name in timestamps:
                    raise ValueError(f"Invalid dump metadata: {name}")
                timestamps[name] = _read_coverage_timestamp(archive, member)
    return sorted(members, key=lambda m: m.name), timestamps


def _insert_parquet_files(
    sources: list[ParquetSource],
    table: str,
    connection: ClickHouseConnection,
    workers: int,
) -> dict:
    """Insert the files in parallel; returns 'total_inserted', 'files_completed' and 'errors'.

    Stops at the first failed file: a failure discards the whole load.
    """
    start_time = time.time()
    total_inserted, files_completed = 0, 0
    errors = []

    def load(source):
        with closing(create_client(connection)) as client:
            return _load_parquet_file(source, table, client)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        try:
            futures = {executor.submit(load, source): source for source in sources}
            for future in as_completed(futures):
                source = futures[future]
                try:
                    total_inserted += future.result()
                except Exception as e:
                    errors.append((str(source), str(e)))
                    logger.error("Error loading %s: %s", source, e)
                    break
                files_completed += 1
                rate = total_inserted / max(time.time() - start_time, 1e-9)
                logger.info(
                    "[%d/%d] %s rows | %s rows/sec",
                    files_completed, len(sources), f"{total_inserted:,}", f"{rate:,.0f}",
                )
        finally:
            # on a failure or shutdown (SystemExit), wait only for the files being loaded
            executor.shutdown(wait=False, cancel_futures=True)
    logger.info("Inserted %s rows into %s in %.1fs", f"{total_inserted:,}", table, time.time() - start_time)
    return {"total_inserted": total_inserted, "files_completed": files_completed, "errors": errors}


def _load_full_dump(parquet_files, connection, workers, client) -> dict:
    # on success the dropped staging table holds the previous listens
    with staging_table(client) as table:
        result = _insert_parquet_files(parquet_files, table, connection, workers)
        if not result["errors"]:
            # Persist this before EXCHANGE: even an ambiguous swap/cleanup failure
            # must not leave an older dataset paired with the previous watermark.
            set_import_state(client, INCREMENTAL_DUMP_STATE, 0)
            swap_in_staged_listens(client, table)
            result["added"] = count_listens(client)
    return result


def _load_incremental_dump(parquet_files, connection, workers, client) -> dict:
    with staging_table(client) as table:
        result = _insert_parquet_files(parquet_files, table, connection, workers)
        if result["errors"]:
            return result

        before = count_listens(client)
        merge_staged_listens(client, table)
        result["added"] = count_listens(client) - before
        logger.info("Added %s new listens (%s in the dump)", f"{result['added']:,}", f"{result['total_inserted']:,}")
        return result


def _load_parquet_files(
    parquet_files: list[ParquetSource],
    connection: ClickHouseConnection,
    dump_type: DumpType = DumpType.INCREMENTAL,
    workers: int = 4,
) -> dict:
    """Load the Parquet files of a dump; a full dump replaces listens. Call _prepare_import first.

    Returns 'total_inserted', 'added', 'files_completed', 'elapsed' and 'errors'.
    """
    start_time = time.time()
    if not parquet_files:
        logger.info("No parquet files in the %s dump", dump_type.value)
        return {"total_inserted": 0, "added": 0, "files_completed": 0, "elapsed": 0, "errors": []}

    logger.info("Loading %s dump: %d parquet files with %d workers", dump_type.value, len(parquet_files), workers)
    load = _load_full_dump if dump_type == DumpType.FULL else _load_incremental_dump
    with closing(create_client(connection, send_receive_timeout=PROCESS_SEND_RECEIVE_TIMEOUT)) as client:
        result = load(parquet_files, connection, workers, client)

    result.setdefault("added", 0)
    result["elapsed"] = time.time() - start_time
    logger.info("Completed in %.1fs", result["elapsed"])
    return result


def _prepare_import(connection: ClickHouseConnection) -> None:
    """Create the schema and drop the leftovers of failed imports.

    TODO: take an import lock here once imports can run concurrently, e.g. more than
      one query worker. Note ClickHouse keeps running the queries of a killed import, so
      the lock must also kill those before letting another import start.
    """
    with closing(create_client(connection)) as client:
        ensure_schema(client)
        drop_import_leftovers(client)


def load_dump(path, connection: ClickHouseConnection, dump_type=DumpType.INCREMENTAL, workers=4) -> dict:
    """Load a directory of Parquet files, or an uncompressed .tar archive of them.

    A local full replacement clears the FTP watermark; use a full FTP import to
    establish verified coverage before automatic catch-up.
    """
    path = Path(path)
    parquet_files = find_parquet_files(path) if path.is_dir() else read_archive(path)[0]
    _prepare_import(connection)
    return _load_parquet_files(parquet_files, connection, dump_type, workers)


def _import_dump(
    downloader: FTPDumpDownloader,
    dump_type: DumpType,
    dump_id: int,
    dump_dir_name: str,
    connection: ClickHouseConnection,
    workers: int,
    download_dir: str | None,
) -> dict:
    """Download a dump from FTP and load it, moving the incremental dump mark to it if it loaded cleanly.

    The dump is downloaded into a temporary directory in ``download_dir`` (default: the system's).
    """
    with TemporaryDirectory(prefix="clickhouse_dump_download_", dir=download_dir) as tmp_dir:
        with downloader:
            archive_path = downloader.download_spark_archive(dump_type, dump_dir_name, tmp_dir)
        logger.info("Downloaded %s dump %d: %s", dump_type.value, dump_id, Path(archive_path).name)
        parquet_files, timestamps = read_archive(Path(archive_path))
        start, end = dump_coverage(timestamps, dump_type)
        if dump_type == DumpType.INCREMENTAL:
            with closing(create_client(connection)) as client:
                covered = get_import_state(client, COVERAGE_STATE)
            if not covered or start > covered:
                raise RuntimeError("Incremental dump coverage gap; import a fresh full dump")
            end = max(end, covered)
        result = _load_parquet_files(parquet_files, connection, dump_type, workers)

    # an incremental dump of a period without new listens has no Parquet files
    if dump_type == DumpType.FULL and not result["files_completed"] and not result["errors"]:
        raise ValueError("Full dump contains no Parquet files; refusing to replace listens")
    result["dump_id"] = dump_id
    if not result["errors"]:
        with closing(create_client(connection)) as client:
            set_import_state(client, COVERAGE_STATE, end)
            set_import_state(client, INCREMENTAL_DUMP_STATE, dump_id)
    return result


def import_latest_full_dump(
    connection: ClickHouseConnection,
    downloader: FTPDumpDownloader,
    *,
    workers: int = 4,
    download_dir: str | None = None,
) -> dict:
    """Download the latest full dump from FTP and load it, replacing listens.

    The incremental dumps are caught up from it.
    """
    _prepare_import(connection)
    with downloader:
        dump_dir_name, dump_id = downloader.get_dump_name(DumpType.FULL)
    logger.info("Loading full dump %d (%s)", dump_id, dump_dir_name)
    return _import_dump(downloader, DumpType.FULL, dump_id, dump_dir_name, connection, workers, download_dir)


def import_missing_incremental_dumps(
    connection: ClickHouseConnection,
    downloader: FTPDumpDownloader,
    *,
    workers: int = 4,
    max_dumps: int | None = None,
    download_dir: str | None = None,
) -> dict:
    """Load the incremental dumps on FTP newer than the incremental dump mark, oldest first.

    Stops at the first failure, so that dump is retried next run rather than skipped.
    ``max_dumps`` limits how many are loaded in this run.

    Returns 'imported' (each with the dumps still 'pending' after it), 'pending',
    'available', 'errors' and 'elapsed'.
    """
    if max_dumps is not None and max_dumps < 1:
        raise ValueError(f"max_dumps must be at least 1, got {max_dumps}")
    start_time = time.time()

    _prepare_import(connection)
    with closing(create_client(connection)) as client:
        last_id = get_import_state(client, INCREMENTAL_DUMP_STATE)
    if not last_id:
        # incremental dumps alone would leave listens without their history
        raise RuntimeError("No full dump imported yet, import one before the incremental dumps")

    with downloader:
        available = downloader.list_dump_ids(DumpType.INCREMENTAL)
    missing = [dump for dump in available if dump[0] > last_id]

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
            result = _import_dump(
                downloader, DumpType.INCREMENTAL, missing_dump_id, dump_dir_name, connection, workers,
                download_dir,
            )
        except Exception as e:
            logger.error("Error loading incremental dump %d: %s", missing_dump_id, e, exc_info=True)
            errors.append((missing_dump_id, str(e)))
            break

        if result["errors"]:
            errors.append((missing_dump_id, describe_load_errors(result["errors"])))
            break

        imported.append(result)
        result["pending"] = pending - len(imported)

    return {
        "imported": imported,
        "pending": pending - len(imported),
        "available": len(available),
        "errors": errors,
        "elapsed": time.time() - start_time,
    }
