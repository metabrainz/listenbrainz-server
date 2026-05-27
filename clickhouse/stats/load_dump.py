#!/usr/bin/env python3
"""
Load listen dumps into ClickHouse.

Supports three sources:
- Pre-extracted directory of Parquet files: load_dump(directory, ...)
- Local dump archive (.tar / .tar.zst): load_from_local(base_dir, ...)
- FTP download: load_from_ftp(dump_type, ...)

Parquet files are inserted into raw_listens in parallel. Once all files are
loaded, a single INSERT...SELECT joins raw_listens against the metadata
tables once and populates the listens table. Joining once at the end (rather
than per batch) collapses metadata-table scans from N-per-batch to 1-per-load.

NOTE: the end-of-load processing reads the entire raw_listens table. Truncate
listens before a fresh load to avoid duplicating already-processed rows.

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
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from clickhouse.stats.ftp import DumpType, FTPDumpDownloader
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
RAW_LISTENS_TABLE = "raw_listens"

RAW_LISTEN_COLUMNS = [
    "listened_at",
    "created",
    "user_id",
    "recording_msid",
    "artist_name",
    "release_name",
    "release_mbid",
    "recording_name",
    "recording_mbid",
    "artist_credit_mbids",
]

# End-of-load: join raw_listens against the deduped metadata tables once
# (no per-batch IN-subquery scans) and populate listens. Grouping by the
# raw_listens UUID is small (16 bytes) and uniquely identifies each source
# row, so all other listen-level columns can be collapsed via any().
PROCESS_RAW_LISTENS = f"""
INSERT INTO {LISTENS_TABLE}
    (
        listened_at,
        created,
        user_id,
        recording_msid,
        submitted_recording_id,
        recording_id,
        submitted_release_group_id,
        release_group_id,
        submitted_artist_ids,
        artist_ids
    )
SELECT
    any(expanded.listened_at) AS listened_at,
    any(expanded.created) AS created,
    any(expanded.user_id) AS user_id,
    any(expanded.recording_msid) AS recording_msid,
    any(expanded.submitted_recording_id) AS submitted_recording_id,
    any(expanded.recording_id) AS recording_id,
    any(expanded.submitted_release_group_id) AS submitted_release_group_id,
    any(expanded.release_group_id) AS release_group_id,
    any(expanded.submitted_artist_ids) AS submitted_artist_ids,
    arrayMap(
        item -> tupleElement(item, 2),
        arraySort(
            item -> tupleElement(item, 1),
            groupArray(tuple(
                expanded.artist_position,
                if(
                    artist.artist_id > 0,
                    artist.artist_id,
                    submittedArtistId(expanded.artist_mbid, expanded.effective_artist_name)
                )
            ))
        )
    ) AS artist_ids
FROM (
    SELECT
        with_release.*,
        artist_position,
        artist_mbid
    FROM (
        SELECT
            base.raw_listen_id,
            base.listened_at,
            base.created,
            base.user_id,
            base.recording_msid,
            base.submitted_recording_id,
            if(base.matched_recording_id > 0, base.matched_recording_id, base.submitted_recording_id) AS recording_id,
            base.submitted_release_group_id,
            if(release.release_group_id > 0, release.release_group_id, base.submitted_release_group_id) AS release_group_id,
            base.submitted_artist_ids,
            base.effective_artist_name,
            base.effective_artist_mbids
        FROM (
            SELECT
                r.raw_listen_id,
                r.listened_at,
                r.created,
                r.user_id,
                r.recording_msid,
                r.artist_name,
                r.release_mbid,
                submittedRecordingId(r.recording_mbid, r.artist_name, r.recording_name) AS submitted_recording_id,
                submittedReleaseGroupId('', r.artist_name, r.release_name) AS submitted_release_group_id,
                arrayMap(
                    mbid -> submittedArtistId(mbid, r.artist_name),
                    if(empty(r.artist_credit_mbids), [''], r.artist_credit_mbids)
                ) AS submitted_artist_ids,
                recording.recording_id AS matched_recording_id,
                if(recording.artist_name != '', recording.artist_name, r.artist_name) AS effective_artist_name,
                if(
                    empty(recording.artist_credit_mbids),
                    if(empty(r.artist_credit_mbids), [''], r.artist_credit_mbids),
                    recording.artist_credit_mbids
                ) AS effective_artist_mbids,
                if(recording.release_mbid != '', recording.release_mbid, r.release_mbid) AS effective_release_mbid
            FROM {RAW_LISTENS_TABLE} AS r
            -- Exclude empty *_mbid rows from the dedup subqueries. The metadata
            -- tables hold a row per distinct artist/recording/release without an
            -- MBID; collapsing them via LIMIT 1 BY '' would pick ONE arbitrary row
            -- and attribute every metadata-less listen to it. By filtering empties
            -- out, those listens fall through to the per-name submitted*Id() hash
            -- below, which keeps distinct artists/recordings separate.
            ANY LEFT JOIN (
                SELECT
                    recording_mbid,
                    recording_id,
                    artist_name,
                    artist_credit_mbids,
                    release_mbid
                FROM recording_metadata
                WHERE recording_mbid != ''
                ORDER BY
                    if(recording_id > 0 AND recording_id <= 4294967295, 0, 1),
                    recording_id
                LIMIT 1 BY recording_mbid
            ) AS recording
                ON r.recording_mbid = recording.recording_mbid
        ) AS base
        ANY LEFT JOIN (
            SELECT
                release_mbid,
                release_group_id
            FROM release_metadata
            WHERE release_mbid != ''
            ORDER BY
                if(release_group_id > 0 AND release_group_id <= 4294967295, 0, 1),
                release_group_id
            LIMIT 1 BY release_mbid
        ) AS release
            ON base.effective_release_mbid = release.release_mbid
    ) AS with_release
    ARRAY JOIN
        arrayEnumerate(effective_artist_mbids) AS artist_position,
        effective_artist_mbids AS artist_mbid
) AS expanded
ANY LEFT JOIN (
    SELECT
        artist_mbid,
        artist_id
    FROM artist_metadata
    WHERE artist_mbid != ''
    ORDER BY
        if(artist_id > 0 AND artist_id <= 4294967295, 0, 1),
        artist_id
    LIMIT 1 BY artist_mbid
) AS artist
    ON expanded.artist_mbid = artist.artist_mbid
GROUP BY expanded.raw_listen_id
"""

# Spill GROUP BY / sort state to disk if the working set exceeds ~8GB.
# join_algorithm='grace_hash' lets the metadata hash-join build sides spill
# too, instead of OOMing when the default hash join can't fit. max_memory_usage
# raises the per-query cap above the 10GB default to give spill enough room
# to actually engage before the memory tracker kills the query.
PROCESS_RAW_LISTENS_SETTINGS = {
    "async_insert": 0,
    "max_bytes_before_external_group_by": 8 * 1024 * 1024 * 1024,
    "max_bytes_before_external_sort": 8 * 1024 * 1024 * 1024,
    "max_memory_usage": 32 * 1024 * 1024 * 1024,
    "join_algorithm": "grace_hash",
    "grace_hash_join_initial_buckets": 16,
}


def _get_config_module():
    """Return the ClickHouse service config module."""
    from clickhouse import config
    return config


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

_STRING_LIST_TYPE = pa.list_(pa.string())


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


def _to_string_list_array(column) -> pa.Array:
    """Replace null outer lists with [] and filter null elements within lists."""
    if isinstance(column, pa.ChunkedArray):
        column = column.combine_chunks()
    if not (pa.types.is_list(column.type) or pa.types.is_large_list(column.type)):
        column = pc.cast(column, _STRING_LIST_TYPE)
    inner_type = column.type.value_type
    if not (pa.types.is_string(inner_type) or pa.types.is_large_string(inner_type)):
        column = pc.cast(column, _STRING_LIST_TYPE)

    column = pc.fill_null(column, pa.scalar([], type=_STRING_LIST_TYPE))

    values = column.values
    if values.null_count == 0:
        return column

    valid_mask = pc.is_valid(values)
    valid_np = valid_mask.to_numpy(zero_copy_only=False)
    offsets_np = column.offsets.to_numpy(zero_copy_only=False).astype(np.int64)

    cum_valid = np.empty(len(valid_np) + 1, dtype=np.int64)
    cum_valid[0] = 0
    np.cumsum(valid_np, out=cum_valid[1:])
    new_offsets = pa.array(cum_valid[offsets_np].astype(np.int32), type=pa.int32())

    return pa.ListArray.from_arrays(new_offsets, values.filter(valid_mask))


def _column_or_default(table: pa.Table, name: str, default: pa.Array) -> pa.Array:
    if name in table.column_names:
        return table[name]
    return default


def build_raw_listens_arrow_table(table: pa.Table) -> pa.Table:
    """Normalize a Spark dump batch into the raw listens table schema."""
    n_rows = table.num_rows
    empty_strings = pa.array([""] * n_rows, type=pa.string())
    empty_lists = pa.array([[]] * n_rows, type=_STRING_LIST_TYPE)

    return pa.table({
        "listened_at": table["listened_at"],
        "created": table["created"],
        "user_id": _to_uint32_array(table["user_id"]),
        "recording_msid": _to_string_array(table["recording_msid"]),
        "artist_name": _to_string_array(_column_or_default(table, "artist_name", empty_strings)),
        "release_name": _to_string_array(_column_or_default(table, "release_name", empty_strings)),
        "release_mbid": _to_string_array(_column_or_default(table, "release_mbid", empty_strings)),
        "recording_name": _to_string_array(_column_or_default(table, "recording_name", empty_strings)),
        "recording_mbid": _to_string_array(_column_or_default(table, "recording_mbid", empty_strings)),
        "artist_credit_mbids": _to_string_list_array(
            _column_or_default(table, "artist_credit_mbids", empty_lists)
        ),
    })


def process_raw_listens(client: Client) -> None:
    """Join raw_listens against the metadata tables once and populate listens."""
    client.command(PROCESS_RAW_LISTENS, settings=PROCESS_RAW_LISTENS_SETTINGS)


# =============================================================================
# Parquet file loading
# =============================================================================

def _load_parquet_file(
    file_path: Path,
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
            listen_table = build_raw_listens_arrow_table(pa.Table.from_batches([batch]))
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
) -> dict:
    """
    Load Parquet dump files from a directory into ClickHouse.

    Returns dict with 'total_inserted', 'files_completed', 'elapsed', 'errors'.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    parquet_files = find_parquet_files(dir_path)
    if not parquet_files:
        logger.info("No parquet files found in %s", directory)
        return {"total_inserted": 0, "files_completed": 0, "elapsed": 0, "errors": []}

    logger.info("Found %d parquet files, loading with %d workers", len(parquet_files), workers)

    client = create_client(host, port, username, password, database)
    logger.info("Connected to ClickHouse at %s:%s", host, port)
    ensure_stats_schema(client)
    client.close()

    progress = LoadProgress()
    start_time = time.time()
    errors = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_load_parquet_file, f, host, port, username, password, database, progress): f
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

    if total_inserted > 0:
        process_client = create_client(
            host, port, username, password, database,
            send_receive_timeout=PROCESS_SEND_RECEIVE_TIMEOUT,
        )
        try:
            logger.info("Processing raw_listens into listens (single end-of-load join)...")
            process_start = time.time()
            process_raw_listens(process_client)
            logger.info("Processed listens in %.1fs", time.time() - process_start)

            raw_count = process_client.query("SELECT count(*) FROM raw_listens").first_row[0]
            processed_count = process_client.query("SELECT count(*) FROM listens").first_row[0]
            logger.info("Total rows in raw_listens: %s", f"{raw_count:,}")
            logger.info("Total rows in listens: %s", f"{processed_count:,}")
        finally:
            process_client.close()

    elapsed = time.time() - start_time
    logger.info("Completed in %.1fs", elapsed)

    return {
        "total_inserted": total_inserted,
        "files_completed": files_completed,
        "elapsed": elapsed,
        "errors": errors,
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

        result = load_dump(str(parquet_dir), host, port, username, password, database, workers)
        result["dump_id"] = found_dump_id
        return result
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


# =============================================================================
# FTP: download then load
# (mirrors listenbrainz_spark/dump/ftp.py::ListenBrainzFtpDumpLoader.download_listens)
# =============================================================================

def load_from_ftp(
    dump_type: DumpType = DumpType.FULL,
    ftp_server: str = None,
    ftp_dir: str = None,
    host: str = "localhost",
    port: int = 8123,
    username: str = "default",
    password: str = "",
    database: str = "default",
    workers: int = 4,
) -> dict:
    """
    Download the latest Spark parquet listens dump from FTP and load it into ClickHouse.

    Mirrors listenbrainz_spark/dump/ftp.py::ListenBrainzFtpDumpLoader.download_listens,
    but targets ClickHouse instead of HDFS/Spark.

    Args:
        dump_type: FULL or INCREMENTAL.
        ftp_server: FTP server hostname; reads from config if not provided.
        ftp_dir: Base FTP directory; reads from config if not provided.

    Returns dict with 'total_inserted', 'files_completed', 'elapsed', 'errors', 'dump_id'.
    """
    if ftp_server is None or ftp_dir is None:
        try:
            config = _get_config_module()
            ftp_server = ftp_server or getattr(config, "FTP_SERVER_URI", "ftp.eu.metabrainz.org")
            ftp_dir = ftp_dir or getattr(config, "FTP_LISTENS_DIR", "/pub/musicbrainz/listenbrainz/")
        except ImportError:
            ftp_server = ftp_server or "ftp.eu.metabrainz.org"
            ftp_dir = ftp_dir or "/pub/musicbrainz/listenbrainz/"

    download_dir = tempfile.mkdtemp(prefix="clickhouse_dump_download_")
    extract_dir = tempfile.mkdtemp(prefix="clickhouse_dump_extract_")

    try:
        downloader = FTPDumpDownloader(ftp_server, ftp_dir)
        downloader.connect()
        try:
            archive_path, dump_id = downloader.download_latest_dump(dump_type, download_dir)
        finally:
            downloader.close()

        logger.info("Downloaded %s dump %d: %s", dump_type.value, dump_id, Path(archive_path).name)

        parquet_dir = _extract_archive(Path(archive_path), Path(extract_dir))
        logger.info("Extracted to %s", parquet_dir)

        result = load_dump(str(parquet_dir), host, port, username, password, database, workers)
        result["dump_id"] = dump_id
        return result
    finally:
        shutil.rmtree(download_dir, ignore_errors=True)
        shutil.rmtree(extract_dir, ignore_errors=True)
