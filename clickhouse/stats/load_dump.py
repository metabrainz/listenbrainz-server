#!/usr/bin/env python3
"""
Load listen dumps into ClickHouse.

Supports three sources:
- Pre-extracted directory of Parquet files: load_dump(directory, ...)
- Local dump archive (.tar / .tar.zst): load_from_local(base_dir, ...)
- FTP download: load_from_ftp(dump_type, ...)

Parquet files are inserted into raw_listens in parallel under a per-load
``load_id`` partition. Once all files are loaded, one INSERT...SELECT copies
that partition into the listens table, then the partition is dropped. Scoping
to the load's partition means earlier loads are never re-processed.

Listens already present in ``listens`` (same user_id, listened_at,
recording_msid), listens deleted in LB (``deleted_listens``) and listens of
users whose history was deleted (``deleted_user_listen_history``) are skipped,
so re-delivered listens (overlapping dumps, retries) are counted once.

Every dump loaded from FTP or a local dump directory is recorded in
``imported_dumps``, which lets ``import_missing_incremental_dumps`` load all the
incremental dumps a missed cron run left behind rather than only the newest one.

A full dump should be loaded with ``replace=True`` which truncates listens and
the cache state first.

The local and FTP paths mirror the patterns in listenbrainz_spark/dump/:
  - dump directories: listenbrainz-dump-{id}-{date}-{tod}-{full|incremental}/
  - archive file inside: listenbrainz-spark-dump-{id}-{date}-{tod}-{full|incremental}.tar
"""

import logging
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from uuid import uuid4

import clickhouse_connect
from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from clickhouse.stats.ftp import DumpType, FTPDumpDownloader
from clickhouse.stats.imported_dumps import (
    get_incremental_dumps_since_latest_full,
    get_latest_full_dump,
    record_imported_dump,
    select_missing_incremental_dumps,
)
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
RAW_LISTENS_TABLE = "raw_listens"

RAW_LISTEN_COLUMNS = [
    "load_id",
    "listened_at",
    "created",
    "user_id",
    "recording_msid",
]

# Source rows for one load: the load's raw_listens partition (optionally one user_id
# bucket of it), minus listens that already exist in `listens`, listens deleted in LB
# and listens of users whose history was deleted, deduplicated on the listen key
# (keeping the most recently created copy).
#
# The IN-sets are kept small: only users present in the load (bucket) are consulted,
# and for `listens` only rows within the load's `created` range -- a re-delivered
# listen has the same `created` as the copy already in `listens`, so nothing outside
# that range can match. A deleted listen is matched on `created` too (like the Spark
# pipeline does): a listen deleted and later re-submitted gets a new `created` and
# must be loaded again.
RAW_LISTENS_SOURCE = """
    SELECT
        r.listened_at AS listened_at,
        r.created AS created,
        r.user_id AS user_id,
        r.recording_msid AS recording_msid
    FROM raw_listens AS r
    LEFT JOIN (
        SELECT user_id, max(max_created) AS max_created
        FROM deleted_user_listen_history
        GROUP BY user_id
    ) AS duh ON r.user_id = duh.user_id
    WHERE r.load_id = {load_id:String} __CHUNK_FILTER_R__
      AND r.created > duh.max_created
      AND (r.user_id, r.listened_at, r.recording_msid) NOT IN (
            SELECT user_id, listened_at, recording_msid
            FROM listens
            WHERE user_id IN (
                SELECT DISTINCT user_id FROM raw_listens
                WHERE load_id = {load_id:String} __CHUNK_FILTER__
            )
              AND created >= (
                SELECT min(created) FROM raw_listens
                WHERE load_id = {load_id:String} __CHUNK_FILTER__
              )
              AND created <= (
                SELECT max(created) FROM raw_listens
                WHERE load_id = {load_id:String} __CHUNK_FILTER__
              )
      )
      AND (r.user_id, r.listened_at, r.recording_msid, r.created) NOT IN (
            SELECT user_id, listened_at, recording_msid, created
            FROM deleted_listens
            WHERE user_id IN (
                SELECT DISTINCT user_id FROM raw_listens
                WHERE load_id = {load_id:String} __CHUNK_FILTER__
            )
      )
    ORDER BY r.user_id, r.listened_at, r.recording_msid, r.created DESC
    LIMIT 1 BY r.user_id, r.listened_at, r.recording_msid
"""

# End-of-load: copy the load's (filtered, deduplicated) raw listens into listens.
PROCESS_RAW_LISTENS = f"""
INSERT INTO {LISTENS_TABLE}
    (listened_at, created, user_id, recording_msid)
SELECT listened_at, created, user_id, recording_msid
FROM (__RAW_LISTENS_SOURCE__)
"""

# Spill the dedup sort and the IN-set hash tables to disk if the working set
# exceeds ~8GB. max_memory_usage raises the per-query cap above the 10GB default
# to give spill enough room to actually engage before the memory tracker kills
# the query.
PROCESS_RAW_LISTENS_SETTINGS = {
    "async_insert": 0,
    "max_bytes_before_external_group_by": 8 * 1024 * 1024 * 1024,
    "max_bytes_before_external_sort": 8 * 1024 * 1024 * 1024,
    "max_memory_usage": 32 * 1024 * 1024 * 1024,
}

# Split PROCESS_RAW_LISTENS into N sequential buckets by user_id % N so peak
# memory and temp-disk per query stay bounded. raw_listens is ORDER BY
# (user_id, ...) so each bucket reads a contiguous slice of granules. The chunk
# count is chosen from the load size: one bucket per
# PROCESS_RAW_LISTENS_ROWS_PER_CHUNK raw rows, so incremental dumps run as a
# single query and a ~1.5B-listen full dump lands around 16 buckets. Lower the
# constant if you see NOT_ENOUGH_SPACE on _tmp_default.
PROCESS_RAW_LISTENS_ROWS_PER_CHUNK = 100_000_000


def choose_process_chunks(total_rows: int) -> int:
    """Pick how many user_id buckets to split the end-of-load join into."""
    return max(1, -(-total_rows // PROCESS_RAW_LISTENS_ROWS_PER_CHUNK))

# Tables holding derived listen data. A full dump load with replace=True truncates
# them so the dump becomes the sole source of truth again. deleted_listens /
# deleted_user_listen_history are kept: they apply to the new data as well.
REPLACE_TRUNCATE_TABLES = [
    LISTENS_TABLE,
    "user_stats_cache_state",
    "stats_cache_state",
]


def build_process_raw_listens_query(chunks: int = 1, chunk: int = 0) -> str:
    """Return the INSERT...SELECT populating listens from one load's raw_listens.

    The load is selected at execution time via the ``load_id`` query parameter.
    With ``chunks > 1`` only the ``user_id % chunks = chunk`` bucket is processed.
    """
    chunk_filter = f"AND user_id % {chunks} = {chunk}" if chunks > 1 else ""
    source = (
        RAW_LISTENS_SOURCE
        .replace("__CHUNK_FILTER_R__", chunk_filter.replace("user_id", "r.user_id"))
        .replace("__CHUNK_FILTER__", chunk_filter)
    )
    return PROCESS_RAW_LISTENS.replace("__RAW_LISTENS_SOURCE__", source)


# =============================================================================
# ClickHouse client
# =============================================================================

class LoadProgress:
    """Thread-safe progress tracker for parallel loading."""

    def __init__(self):
        self.lock = Lock()
        self.total_inserted = 0
        self.files_completed = 0

    def update(self, rows: int):
        with self.lock:
            self.total_inserted += rows
            self.files_completed += 1

    def get(self) -> tuple[int, int]:
        with self.lock:
            return self.total_inserted, self.files_completed


PROCESS_SEND_RECEIVE_TIMEOUT = 7200


def create_client(
    host: str, port: int, username: str, password: str, database: str,
    send_receive_timeout: int = 300,
) -> Client:
    return clickhouse_connect.get_client(
        host=host, port=port, username=username, password=password, database=database,
        compress=False,
        form_encode_query_params=True,
        session_id=f"listenbrainz_load_dump_{uuid4().hex}",
        settings={"async_insert": 1, "wait_for_async_insert": 1},
        send_receive_timeout=send_receive_timeout,
    )


# =============================================================================
# Arrow transform
# =============================================================================

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


def build_raw_listens_arrow_table(table: pa.Table, load_id: str) -> pa.Table:
    """Normalize a Spark dump batch into the raw listens table schema."""
    return pa.table({
        "load_id": pa.array([load_id] * table.num_rows, type=pa.string()),
        "listened_at": table["listened_at"],
        "created": table["created"],
        "user_id": _to_uint32_array(table["user_id"]),
        "recording_msid": _to_string_array(table["recording_msid"]),
    })


def process_raw_listens(client: Client, load_id: str, chunks: int = 1) -> None:
    """Copy one load's raw_listens into listens, skipping existing and deleted listens.

    Runs in ``chunks`` sequential buckets keyed by ``user_id % chunks`` so each
    query's sort / IN-set state stays bounded. ``chunks=1`` runs it as a single
    query (only safe on small inputs or with plenty of temp-disk headroom); see
    :func:`choose_process_chunks`.
    """
    parameters = {"load_id": load_id}
    if chunks <= 1:
        client.command(
            build_process_raw_listens_query(), parameters=parameters, settings=PROCESS_RAW_LISTENS_SETTINGS
        )
        return

    for i in range(chunks):
        logger.info("Processing raw_listens bucket %d/%d", i + 1, chunks)
        t0 = time.time()
        client.command(
            build_process_raw_listens_query(chunks, i), parameters=parameters, settings=PROCESS_RAW_LISTENS_SETTINGS
        )
        logger.info("Bucket %d/%d done in %.1fs", i + 1, chunks, time.time() - t0)


def drop_raw_listens_partition(client: Client, load_id: str) -> None:
    """Drop the staging partition of a load (no-op if it does not exist)."""
    client.command(
        "ALTER TABLE raw_listens DROP PARTITION {load_id:String}",
        parameters={"load_id": load_id},
    )


def truncate_derived_tables(client: Client) -> None:
    """Truncate listens and cache state ahead of a replacing full dump load."""
    for table in REPLACE_TRUNCATE_TABLES:
        logger.info("Truncating %s", table)
        client.command(f"TRUNCATE TABLE IF EXISTS {table}")


# =============================================================================
# Parquet file loading
# =============================================================================

def _load_parquet_file(
    file_path: Path,
    load_id: str,
    host: str, port: int, username: str, password: str, database: str,
    progress: LoadProgress = None,
    batch_size: int = 200_000,
) -> int:
    client = create_client(host, port, username, password, database)
    try:
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows
        if total_rows == 0:
            return 0

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            listen_table = build_raw_listens_arrow_table(pa.Table.from_batches([batch]), load_id)
            client.insert_arrow(
                table=RAW_LISTENS_TABLE,
                arrow_table=listen_table,
            )

        if progress:
            progress.update(total_rows)
        return total_rows
    finally:
        client.close()


def find_parquet_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.parquet"))


# =============================================================================
# Core: load from a directory of Parquet files
# =============================================================================

def load_dump(
    directory: str,
    host: str = "localhost",
    port: int = 8123,
    username: str = "default",
    password: str = "",
    database: str = "default",
    workers: int = 4,
    process_chunks: int | None = None,
    replace: bool = False,
) -> dict:
    """
    Load Parquet dump files from a directory into ClickHouse.

    Args:
        process_chunks: number of user_id buckets for the end-of-load join;
            ``None`` picks it from the number of raw rows loaded
            (see :func:`choose_process_chunks`).
        replace: truncate listens and the cache state before loading (full
            dump semantics). Deleted-listen records are kept.

    Returns dict with 'total_inserted', 'files_completed', 'elapsed', 'errors', 'load_id'.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    parquet_files = find_parquet_files(dir_path)
    load_id = uuid4().hex
    if not parquet_files:
        logger.info("No parquet files found in %s", directory)
        return {"total_inserted": 0, "files_completed": 0, "elapsed": 0, "errors": [], "load_id": load_id}

    logger.info("Found %d parquet files, loading with %d workers (load_id=%s)", len(parquet_files), workers, load_id)

    client = create_client(host, port, username, password, database)
    logger.info("Connected to ClickHouse at %s:%s", host, port)
    ensure_stats_schema(client)
    if replace:
        truncate_derived_tables(client)
    client.close()

    progress = LoadProgress()
    start_time = time.time()
    errors = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_load_parquet_file, f, load_id, host, port, username, password, database, progress): f
            for f in parquet_files
        }
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                future.result()
                total, completed = progress.get()
                elapsed = time.time() - start_time
                rate = total / elapsed if elapsed > 0 else 0
                logger.info("[%d/%d] %s rows | %s rows/sec", completed, len(parquet_files), f"{total:,}", f"{rate:,.0f}")
            except Exception as e:
                errors.append((str(file_path), str(e)))
                logger.error("Error loading %s: %s", file_path, e)

    ingest_elapsed = time.time() - start_time
    total_inserted, files_completed = progress.get()
    logger.info(
        "Ingested %s rows into raw_listens in %.1fs",
        f"{total_inserted:,}", ingest_elapsed,
    )

    if errors:
        logger.error("%d errors:", len(errors))
        for path, error in errors[:10]:
            logger.error("  %s: %s", path, error)

    process_client = create_client(
        host, port, username, password, database,
        send_receive_timeout=PROCESS_SEND_RECEIVE_TIMEOUT,
    )
    try:
        if errors:
            # Leave the partition in place for inspection; the retry (a new load_id)
            # skips whatever this load already got into listens. Nothing was
            # processed into listens, so no double counting either way.
            logger.error("Skipping processing of load %s because %d file(s) failed", load_id, len(errors))
        elif total_inserted > 0:
            chunks = process_chunks if process_chunks is not None else choose_process_chunks(total_inserted)
            logger.info(
                "Processing raw_listens into listens (%s raw rows, %d chunks)...",
                f"{total_inserted:,}", chunks,
            )
            process_start = time.time()
            before = process_client.query("SELECT count(*) FROM listens").first_row[0]
            process_raw_listens(process_client, load_id, chunks=chunks)
            after = process_client.query("SELECT count(*) FROM listens").first_row[0]
            logger.info(
                "Processed listens in %.1fs: %s new listens (%s raw rows), %s total",
                time.time() - process_start, f"{after - before:,}", f"{total_inserted:,}", f"{after:,}",
            )
            drop_raw_listens_partition(process_client, load_id)
    finally:
        process_client.close()

    elapsed = time.time() - start_time
    logger.info("Completed in %.1fs", elapsed)

    return {
        "total_inserted": total_inserted,
        "files_completed": files_completed,
        "elapsed": elapsed,
        "errors": errors,
        "load_id": load_id,
    }


# =============================================================================
# Archive extraction
# =============================================================================

def _extract_archive(archive_path: Path, extract_dir: Path) -> Path:
    """
    Extract a .tar or .tar.zst dump archive.

    Returns the path to the directory containing the extracted Parquet files.
    Mirrors the extraction step in the Spark dump pipeline.
    """
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

    # If the archive extracted into a subdirectory, return that; otherwise the extract_dir itself
    subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
    return subdirs[0] if subdirs else extract_dir


# =============================================================================
# Local: find dump archive in a local directory tree
# (mirrors listenbrainz_spark/dump/local.py)
# =============================================================================

def _find_dump_archive(base_dir: Path, dump_id: int = None, dump_type: DumpType = DumpType.FULL) -> tuple[Path, int]:
    """
    Find a Spark parquet listens dump archive in a local directory.

    Expects the same directory structure used by the ListenBrainz dump pipeline:
        base_dir/
            listenbrainz-dump-{id}-{date}-{tod}-{full|incremental}/
                listenbrainz-spark-dump-{id}-{date}-{tod}-{full|incremental}.tar

    Mirrors listenbrainz_spark/dump/local.py::ListenbrainzLocalDumpLoader.load_listens.

    Returns (archive_path, dump_id).
    """
    suffix = f"-{dump_type.value}"
    dump_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("listenbrainz-dump-") and d.name.endswith(suffix)],
        key=lambda d: int(d.name.split("-")[2]),
    )

    if not dump_dirs:
        raise ValueError(f"No {dump_type.value} dump directories found in {base_dir}")

    if dump_id is not None:
        matches = [d for d in dump_dirs if int(d.name.split("-")[2]) == dump_id]
        if not matches:
            raise ValueError(f"Dump {dump_id} not found in {base_dir}")
        dump_dir = matches[0]
    else:
        dump_dir = dump_dirs[-1]

    found_id = int(dump_dir.name.split("-")[2])

    archives = [
        f for f in dump_dir.iterdir()
        if "spark-dump" in f.name and (f.name.endswith(".tar.zst") or f.name.endswith(".tar"))
    ]
    if not archives:
        raise ValueError(f"No Spark parquet listens archive found in {dump_dir}")

    return archives[0], found_id


def load_from_local(
    base_dir: str,
    dump_id: int = None,
    dump_type: DumpType = DumpType.FULL,
    host: str = "localhost",
    port: int = 8123,
    username: str = "default",
    password: str = "",
    database: str = "default",
    workers: int = 4,
    process_chunks: int | None = None,
    replace: bool = False,
) -> dict:
    """
    Load a Spark parquet listens dump from a local directory into ClickHouse.

    Locates the dump archive under base_dir (same directory structure as the
    ListenBrainz dump pipeline), extracts it, and loads the Parquet files.

    Args:
        base_dir: Directory containing listenbrainz-dump-* subdirectories.
        dump_id: Specific dump ID to load; defaults to the latest available.
        dump_type: FULL or INCREMENTAL.

    Returns dict with 'total_inserted', 'files_completed', 'elapsed', 'errors', 'dump_id'.
    """
    extract_dir = tempfile.mkdtemp(prefix="clickhouse_dump_extract_")
    try:
        archive_path, found_dump_id = _find_dump_archive(Path(base_dir), dump_id, dump_type)
        logger.info("Found %s dump %d: %s", dump_type.value, found_dump_id, archive_path.name)

        parquet_dir = _extract_archive(archive_path, Path(extract_dir))
        logger.info("Extracted to %s", parquet_dir)

        result = load_dump(
            str(parquet_dir), host, port, username, password, database, workers,
            process_chunks=process_chunks, replace=replace,
        )
        result["dump_id"] = found_dump_id
        if not result["errors"]:
            _record_dump_import(found_dump_id, dump_type, host, port, username, password, database)
        return result
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


# =============================================================================
# FTP: download then load
# (mirrors listenbrainz_spark/dump/ftp.py::ListenBrainzFtpDumpLoader.download_listens)
# =============================================================================

def _record_dump_import(
    dump_id: int, dump_type: DumpType,
    host: str, port: int, username: str, password: str, database: str,
) -> None:
    """Note in ClickHouse that ``dump_id`` is now part of the listens table."""
    client = create_client(host, port, username, password, database)
    try:
        record_imported_dump(client, dump_id, dump_type)
    finally:
        client.close()


def load_from_ftp(
    *,
    dump_type: DumpType,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    workers: int = 4,
    process_chunks: int | None = None,
    replace: bool = False,
    dump_id: int | None = None,
) -> dict:
    """
    Download a Spark parquet listens dump from FTP and load it into ClickHouse.

    Mirrors listenbrainz_spark/dump/ftp.py::ListenBrainzFtpDumpLoader.download_listens,
    but targets ClickHouse instead of HDFS/Spark.

    A dump that loads cleanly is recorded in ``imported_dumps`` so a later catch-up
    knows not to load it again; a load that left parquet files behind is not, so the
    next run retries it.

    Args:
        dump_type: FULL or INCREMENTAL.
        dump_id: Specific dump id to load; defaults to the latest available.

    Returns dict with 'total_inserted', 'files_completed', 'elapsed', 'errors', 'dump_id'.
    """
    download_dir = tempfile.mkdtemp(prefix="clickhouse_dump_download_")
    extract_dir = tempfile.mkdtemp(prefix="clickhouse_dump_extract_")

    try:
        downloader = FTPDumpDownloader()
        downloader.connect()
        try:
            archive_path, loaded_dump_id = downloader.download_dump_archive(dump_type, download_dir, dump_id)
        finally:
            downloader.close()

        logger.info("Downloaded %s dump %d: %s", dump_type.value, loaded_dump_id, Path(archive_path).name)

        parquet_dir = _extract_archive(Path(archive_path), Path(extract_dir))
        logger.info("Extracted to %s", parquet_dir)

        result = load_dump(
            str(parquet_dir), host, port, username, password, database, workers,
            process_chunks=process_chunks, replace=replace,
        )
        result["dump_id"] = loaded_dump_id
        if not result["errors"]:
            _record_dump_import(loaded_dump_id, dump_type, host, port, username, password, database)
        return result
    finally:
        shutil.rmtree(download_dir, ignore_errors=True)
        shutil.rmtree(extract_dir, ignore_errors=True)


def import_missing_incremental_dumps(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    workers: int = 4,
    process_chunks: int | None = None,
    max_dumps: int | None = None,
) -> dict:
    """
    Load every incremental dump on the FTP server that is not in listens yet.

    The dumps still to load are the ones newer than the last full dump import that
    ``imported_dumps`` has no record of, loaded oldest first. Loading stops at the
    first failure rather than skipping past it, so the failed dump is retried on the
    next run instead of becoming a permanent hole in the listen history.

    Args:
        max_dumps: Load at most this many dumps in one run; the rest are picked up by
            the next run. ``None`` loads the whole backlog.

    Returns dict with 'imported', 'pending', 'available', 'errors', 'elapsed'.
    """
    start_time = time.time()

    client = create_client(host, port, username, password, database)
    try:
        ensure_stats_schema(client)
        latest_full_dump = get_latest_full_dump(client)
        imported_ids = get_incremental_dumps_since_latest_full(client)
    finally:
        client.close()

    downloader = FTPDumpDownloader()
    downloader.connect()
    try:
        available = downloader.list_dump_ids(DumpType.INCREMENTAL)
    finally:
        downloader.close()

    if latest_full_dump is None:
        # Incremental dumps only make sense on top of a full dump. Without a record of
        # one there is no id to catch up from -- loading every incremental the server
        # still keeps would be wrong -- so take the newest one, as the Spark pipeline does.
        logger.warning(
            "No full dump recorded in imported_dumps; loading only the latest incremental dump. "
            "Run a full dump import to enable catch-up."
        )
        missing = [dump for dump in available[-1:] if dump[0] not in imported_ids]
    else:
        missing = select_missing_incremental_dumps(available, imported_ids, latest_full_dump["dump_id"])

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
                dump_type=DumpType.INCREMENTAL,
                host=host, port=port, username=username, password=password, database=database,
                workers=workers, process_chunks=process_chunks, replace=False,
                dump_id=missing_dump_id,
            )
        except Exception as e:
            logger.error("Error loading incremental dump %d: %s", missing_dump_id, e, exc_info=True)
            errors.append((missing_dump_id, str(e)))
            break

        if result["errors"]:
            examples = "; ".join(f"{path}: {error}" for path, error in result["errors"][:3])
            errors.append((missing_dump_id, f"{len(result['errors'])} parquet file(s) failed to load: {examples}"))
            break

        imported.append(result)

    return {
        "imported": imported,
        "pending": pending - len(imported),
        "available": len(available),
        "errors": errors,
        "elapsed": time.time() - start_time,
    }
