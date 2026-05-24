#!/usr/bin/env python3
"""
Load listen dumps into ClickHouse.

Supports three sources:
- Pre-extracted directory of Parquet files: load_dump(directory, ...)
- Local dump archive (.tar / .tar.zst): load_from_local(base_dir, ...)
- FTP download: load_from_ftp(dump_type, ...)

Rows are inserted into the raw listens table, then processed in bounded
ClickHouse batches into the id-only listens table.

The local and FTP paths mirror the patterns in listenbrainz_spark/dump/:
  - dump directories: listenbrainz-dump-{id}-{date}-{tod}-{full|incremental}/
  - archive file inside: listenbrainz-spark-dump-{id}-{date}-{tod}-{full|incremental}.tar
"""

import logging
import math
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import clickhouse_connect
from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.parquet as pq

from clickhouse.stats.ftp import DumpType, FTPDumpDownloader
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
RAW_LISTENS_TABLE = "raw_listens"
RAW_LISTENS_BATCH_TABLE = "raw_listens_batch"

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

RAW_LISTEN_BATCH_COLUMNS = ["batch_row_id"] + RAW_LISTEN_COLUMNS

CREATE_RAW_LISTENS_BATCH_TABLE = f"""
CREATE TEMPORARY TABLE IF NOT EXISTS {RAW_LISTENS_BATCH_TABLE} (
    batch_row_id UInt64,
    listened_at DateTime64(3),
    created DateTime64(3),
    user_id UInt32,
    recording_msid String,
    artist_name String,
    release_name String,
    release_mbid String,
    recording_name String,
    recording_mbid String,
    artist_credit_mbids Array(String)
) ENGINE = Memory
"""

PROCESS_RAW_LISTENS_BATCH = f"""
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
    expanded.listened_at,
    expanded.created,
    expanded.user_id,
    expanded.recording_msid,
    expanded.submitted_recording_id,
    expanded.recording_id,
    expanded.submitted_release_group_id,
    expanded.release_group_id,
    expanded.submitted_artist_ids,
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
            base.batch_row_id,
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
                r.batch_row_id,
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
            FROM {RAW_LISTENS_BATCH_TABLE} AS r
            ANY LEFT JOIN (
                SELECT
                    recording_mbid,
                    recording_id,
                    artist_name,
                    artist_credit_mbids,
                    release_mbid
                FROM recording_metadata
                WHERE recording_mbid IN (
                    SELECT DISTINCT recording_mbid
                    FROM {RAW_LISTENS_BATCH_TABLE}
                    WHERE recording_mbid != ''
                )
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
            WHERE release_mbid IN (
                SELECT DISTINCT release_mbid
                FROM {RAW_LISTENS_BATCH_TABLE}
                WHERE release_mbid != ''
            )
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
    WHERE artist_mbid IN (
        SELECT DISTINCT artist_mbid
        FROM (
            SELECT arrayJoin(if(empty(artist_credit_mbids), [''], artist_credit_mbids)) AS artist_mbid
            FROM {RAW_LISTENS_BATCH_TABLE}
            UNION DISTINCT
            SELECT arrayJoin(if(empty(artist_credit_mbids), [''], artist_credit_mbids)) AS artist_mbid
            FROM recording_metadata
            WHERE recording_mbid IN (
                SELECT DISTINCT recording_mbid
                FROM {RAW_LISTENS_BATCH_TABLE}
                WHERE recording_mbid != ''
            )
        ) AS batch_artist_mbids
        WHERE artist_mbid != ''
    )
    ORDER BY
        if(artist_id > 0 AND artist_id <= 4294967295, 0, 1),
        artist_id
    LIMIT 1 BY artist_mbid
) AS artist
    ON expanded.artist_mbid = artist.artist_mbid
GROUP BY
    expanded.batch_row_id,
    expanded.listened_at,
    expanded.created,
    expanded.user_id,
    expanded.recording_msid,
    expanded.submitted_recording_id,
    expanded.recording_id,
    expanded.submitted_release_group_id,
    expanded.release_group_id,
    expanded.submitted_artist_ids
"""


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


def create_client(host: str, port: int, username: str, password: str, database: str) -> Client:
    return clickhouse_connect.get_client(
        host=host, port=port, username=username, password=password, database=database,
        compress=False,
        form_encode_query_params=True,
        session_id=f"listenbrainz_load_dump_{uuid4().hex}",
        settings={"async_insert": 1, "wait_for_async_insert": 1},
    )


# =============================================================================
# Arrow transform
# =============================================================================

def clean_array(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, str):
        return [value] if value else []
    return [item for item in value if item is not None]


def _is_null(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    return False


def _clean_scalar(value, default=""):
    return default if _is_null(value) else value


def _clean_int(value) -> int:
    return 0 if _is_null(value) else int(value)


def _normalise_listen_row(row: dict) -> dict:
    return {
        "listened_at": row["listened_at"],
        "created": row["created"],
        "user_id": _clean_int(row["user_id"]),
        "recording_msid": str(_clean_scalar(row["recording_msid"])),
        "artist_name": str(_clean_scalar(row.get("artist_name"))),
        "release_name": str(_clean_scalar(row.get("release_name"))),
        "release_mbid": str(_clean_scalar(row.get("release_mbid"))),
        "recording_name": str(_clean_scalar(row.get("recording_name"))),
        "recording_mbid": str(_clean_scalar(row.get("recording_mbid"))),
        "artist_credit_mbids": [str(value) for value in clean_array(row.get("artist_credit_mbids"))],
    }


def build_raw_listens_arrow_table(table: pa.Table, include_batch_row_id: bool = False) -> pa.Table:
    """Normalize a Spark dump batch into the raw listens table schema."""
    listen_rows = [
        _normalise_listen_row(row)
        for row in table.to_pylist()
    ]
    columns = {
        column: [row[column] for row in listen_rows]
        for column in RAW_LISTEN_COLUMNS
    }
    if include_batch_row_id:
        columns = {"batch_row_id": list(range(len(listen_rows))), **columns}

    return pa.table(columns)


def create_raw_listens_batch_table(client: Client) -> None:
    client.command(CREATE_RAW_LISTENS_BATCH_TABLE)


def process_raw_listens_batch(client: Client, table: pa.Table) -> None:
    batch_table = build_raw_listens_arrow_table(table, include_batch_row_id=True)
    client.command(f"TRUNCATE TABLE {RAW_LISTENS_BATCH_TABLE}")
    client.insert_arrow(
        table=RAW_LISTENS_BATCH_TABLE,
        arrow_table=batch_table,
        settings={"async_insert": 0},
    )
    client.command(PROCESS_RAW_LISTENS_BATCH, settings={"async_insert": 0})


# =============================================================================
# Parquet file loading
# =============================================================================

def _load_parquet_file(
    file_path: Path,
    host: str, port: int, username: str, password: str, database: str,
    progress: LoadProgress = None,
    batch_size: int = 10_000,
) -> int:
    client = create_client(host, port, username, password, database)
    try:
        create_raw_listens_batch_table(client)
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows
        if total_rows == 0:
            return 0

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            batch_table = pa.Table.from_batches([batch])
            listen_table = build_raw_listens_arrow_table(batch_table)
            client.insert_arrow(
                table=RAW_LISTENS_TABLE,
                arrow_table=listen_table,
            )
            process_raw_listens_batch(client, batch_table)

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

    elapsed = time.time() - start_time
    total_inserted, files_completed = progress.get()
    logger.info("Completed in %.1fs, %s rows inserted", elapsed, f"{total_inserted:,}")

    if errors:
        logger.error("%d errors:", len(errors))
        for path, error in errors[:10]:
            logger.error("  %s: %s", path, error)

    if total_inserted > 0:
        verify_client = create_client(host, port, username, password, database)
        raw_count = verify_client.query("SELECT count(*) FROM raw_listens").first_row[0]
        processed_count = verify_client.query("SELECT count(*) FROM listens").first_row[0]
        logger.info("Total rows in raw_listens: %s", f"{raw_count:,}")
        logger.info("Total rows in listens: %s", f"{processed_count:,}")
        verify_client.close()

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
