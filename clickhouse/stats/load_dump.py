#!/usr/bin/env python3
"""
Load listen dumps into ClickHouse.

Supports three sources:
- Pre-extracted directory of Parquet files: load_dump(directory, ...)
- Local dump archive (.tar / .tar.zst): load_from_local(base_dir, ...)
- FTP download: load_from_ftp(dump_type, ...)

Rows are transformed into submitted/effective entity IDs before insertion into
the id-only listens fact table. Submitted metadata rows are upserted alongside
the listens so fallback/hash IDs remain displayable.

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

import clickhouse_connect
from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.parquet as pq

from clickhouse.stats.ftp import DumpType, FTPDumpDownloader
from clickhouse.stats.schema import ensure_stats_schema

logger = logging.getLogger(__name__)

LISTENS_TABLE = "listens"
MUSICBRAINZ_ID_MAX = 0xffffffff

LISTEN_COLUMNS = [
    "listened_at",
    "created",
    "user_id",
    "recording_msid",
    "submitted_recording_id",
    "recording_id",
    "submitted_release_group_id",
    "release_group_id",
    "submitted_artist_ids",
    "artist_ids",
]

METADATA_COLUMNS = {
    "artist_metadata": ["artist_id", "artist_mbid", "artist_name", "country_code"],
    "recording_metadata": [
        "recording_id", "recording_mbid", "recording_name", "artist_name",
        "artist_credit_mbids", "release_name", "release_mbid", "artists",
        "caa_id", "caa_release_mbid",
    ],
    "release_group_metadata": [
        "release_group_id", "release_group_mbid", "release_group_name", "artist_name",
        "artist_credit_mbids", "artists", "caa_id", "caa_release_mbid",
        "first_release_date_year", "primary_type",
    ],
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


def create_client(host: str, port: int, username: str, password: str, database: str) -> Client:
    return clickhouse_connect.get_client(
        host=host, port=port, username=username, password=password, database=database,
        compress=False,
        settings={"async_insert": 1, "wait_for_async_insert": 0},
    )


# =============================================================================
# Arrow transform
# =============================================================================

def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


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


def is_musicbrainz_id(value: Any) -> bool:
    return 0 < int(value or 0) <= MUSICBRAINZ_ID_MAX


def build_submitted_metadata_rows(row: dict[str, Any], ids: dict[str, Any]) -> dict[str, list[tuple]]:
    """Return metadata rows for submitted/hash IDs derived from a listen."""
    artist_name = _clean_str(row.get("artist_name"))
    release_name = _clean_str(row.get("release_name"))
    release_mbid = _clean_str(row.get("release_mbid"))
    recording_name = _clean_str(row.get("recording_name"))
    recording_mbid = _clean_str(row.get("recording_mbid"))
    release_group_mbid = _clean_str(row.get("release_group_mbid"))
    artist_credit_mbids = clean_array(row.get("artist_credit_mbids")) or [""]

    return {
        "artist_metadata": [
            (artist_id, _clean_str(mbid), artist_name, "")
            for artist_id, mbid in zip(ids["submitted_artist_ids"], artist_credit_mbids)
        ],
        "recording_metadata": [(
            ids["submitted_recording_id"],
            recording_mbid,
            recording_name,
            artist_name,
            artist_credit_mbids,
            release_name,
            release_mbid,
            "",
            0,
            "",
        )],
        "release_group_metadata": [] if ids["submitted_release_group_id"] == 0 else [(
            ids["submitted_release_group_id"],
            release_group_mbid,
            release_name,
            artist_name,
            artist_credit_mbids,
            "",
            0,
            "",
            0,
            "",
        )],
    }


def dedupe_metadata_rows(metadata_rows: dict[str, list[tuple]]) -> dict[str, list[tuple]]:
    """Keep one submitted metadata row per entity ID for each table."""
    deduped = {}
    for table_name, rows in metadata_rows.items():
        by_id = {}
        for row in rows:
            if row and row[0] != 0:
                by_id[row[0]] = row
        deduped[table_name] = list(by_id.values())
    return deduped


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


def _keep_preferred_entity(
    entities: dict[str, dict],
    key: str,
    candidate: dict,
    id_key: str,
) -> None:
    if not key:
        return
    existing = entities.get(key)
    if existing is None or (is_musicbrainz_id(candidate[id_key]) and not is_musicbrainz_id(existing[id_key])):
        entities[key] = candidate


def lookup_recording_metadata(client: Client, recording_mbids: set[str]) -> dict[str, dict]:
    recording_mbids = {mbid for mbid in recording_mbids if mbid}
    if not recording_mbids:
        return {}

    result = client.query("""
        SELECT
            recording_mbid,
            recording_id,
            recording_name,
            artist_name,
            artist_credit_mbids,
            release_name,
            release_mbid
        FROM recording_metadata FINAL
        WHERE recording_mbid IN {recording_mbids:Array(String)}
          AND recording_mbid != ''
    """, parameters={"recording_mbids": sorted(recording_mbids)})

    recordings: dict[str, dict] = {}
    for row in result.result_rows:
        candidate = {
            "recording_mbid": row[0] or "",
            "recording_id": int(row[1] or 0),
            "recording_name": row[2] or "",
            "artist_name": row[3] or "",
            "artist_credit_mbids": clean_array(row[4]),
            "release_name": row[5] or "",
            "release_mbid": row[6] or "",
        }
        _keep_preferred_entity(recordings, candidate["recording_mbid"], candidate, "recording_id")
    return recordings


def lookup_artist_metadata(client: Client, artist_mbids: set[str]) -> dict[str, dict]:
    artist_mbids = {mbid for mbid in artist_mbids if mbid}
    if not artist_mbids:
        return {}

    result = client.query("""
        SELECT artist_mbid, artist_id, artist_name
        FROM artist_metadata FINAL
        WHERE artist_mbid IN {artist_mbids:Array(String)}
          AND artist_mbid != ''
    """, parameters={"artist_mbids": sorted(artist_mbids)})

    artists: dict[str, dict] = {}
    for row in result.result_rows:
        candidate = {
            "artist_mbid": row[0] or "",
            "artist_id": int(row[1] or 0),
            "artist_name": row[2] or "",
        }
        _keep_preferred_entity(artists, candidate["artist_mbid"], candidate, "artist_id")
    return artists


def lookup_release_metadata(client: Client, release_mbids: set[str]) -> dict[str, dict]:
    release_mbids = {mbid for mbid in release_mbids if mbid}
    if not release_mbids:
        return {}

    result = client.query("""
        SELECT
            release_mbid,
            release_group_id,
            release_group_mbid,
            release_name,
            album_artist_name,
            artist_credit_mbids
        FROM release_metadata FINAL
        WHERE release_mbid IN {release_mbids:Array(String)}
          AND release_mbid != ''
    """, parameters={"release_mbids": sorted(release_mbids)})

    releases: dict[str, dict] = {}
    for row in result.result_rows:
        candidate = {
            "release_mbid": row[0] or "",
            "release_group_id": int(row[1] or 0),
            "release_group_mbid": row[2] or "",
            "release_name": row[3] or "",
            "artist_name": row[4] or "",
            "artist_credit_mbids": clean_array(row[5]),
        }
        _keep_preferred_entity(releases, candidate["release_mbid"], candidate, "release_group_id")
    return releases


def calculate_submitted_entity_ids(client: Client, listens: list[dict]) -> list[dict]:
    """Calculate submitted IDs in ClickHouse using the schema UDFs."""
    if not listens:
        return []

    result = client.query("""
        SELECT
            submittedRecordingId(
                tupleElement(row, 4),
                tupleElement(row, 1),
                tupleElement(row, 3)
            ) AS submitted_recording_id,
            submittedReleaseGroupId('', tupleElement(row, 1), tupleElement(row, 5)) AS submitted_release_group_id,
            arrayMap(
                mbid -> submittedArtistId(mbid, tupleElement(row, 1)),
                if(empty(tupleElement(row, 2)), [''], tupleElement(row, 2))
            ) AS submitted_artist_ids
        FROM (
            SELECT arrayJoin({rows:Array(Tuple(String, Array(String), String, String, String))}) AS row
        )
    """, parameters={
        "rows": [
            (
                listen["artist_name"],
                listen["artist_credit_mbids"],
                listen["recording_name"],
                listen["recording_mbid"],
                listen["release_name"],
            )
            for listen in listens
        ],
    })

    return [
        {
            "submitted_recording_id": int(row[0] or 0),
            "submitted_release_group_id": int(row[1] or 0),
            "submitted_artist_ids": [int(value or 0) for value in clean_array(row[2])],
        }
        for row in result.result_rows
    ]


def calculate_submitted_artist_ids(client: Client, artist_pairs: set[tuple[str, str]]) -> dict[tuple[str, str], int]:
    """Calculate fallback artist IDs in ClickHouse for arbitrary (mbid, name) pairs."""
    if not artist_pairs:
        return {}

    pairs = sorted(artist_pairs)
    result = client.query("""
        SELECT
            tupleElement(row, 1) AS artist_mbid,
            tupleElement(row, 2) AS artist_name,
            submittedArtistId(tupleElement(row, 1), tupleElement(row, 2)) AS artist_id
        FROM (
            SELECT arrayJoin({pairs:Array(Tuple(String, String))}) AS row
        )
    """, parameters={"pairs": pairs})

    return {
        (row[0] or "", row[1] or ""): int(row[2] or 0)
        for row in result.result_rows
    }


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


def _resolve_artist_ids(
    artist_name: str,
    artist_credit_mbids: list[str],
    fallback_artist_ids: dict[tuple[str, str], int],
    artist_metadata: dict[str, dict],
) -> tuple[list[int], list[tuple]]:
    artist_credit_mbids = artist_credit_mbids or [""]
    artist_ids = []
    metadata_rows = []

    for artist_mbid in artist_credit_mbids:
        artist = artist_metadata.get(artist_mbid)
        if artist is not None and artist["artist_id"] != 0:
            artist_ids.append(artist["artist_id"])
            continue

        artist_id = fallback_artist_ids[(artist_mbid, artist_name)]
        artist_ids.append(artist_id)
        metadata_rows.append((artist_id, artist_mbid, artist_name, ""))

    return artist_ids, metadata_rows


def transform_listen_rows(listens: list[dict], client: Client) -> tuple[list[list], dict[str, list[tuple]]]:
    """Transform normalized listen rows using ClickHouse metadata lookups only."""
    submitted_ids_by_listen = calculate_submitted_entity_ids(client, listens)
    if len(submitted_ids_by_listen) != len(listens):
        raise RuntimeError("ClickHouse returned an unexpected submitted ID row count")

    recording_metadata = lookup_recording_metadata(
        client,
        {listen["recording_mbid"] for listen in listens},
    )

    artist_mbids = set()
    release_mbids = set()
    for listen in listens:
        recording = recording_metadata.get(listen["recording_mbid"])
        if recording is not None:
            artist_mbids.update(recording["artist_credit_mbids"] or listen["artist_credit_mbids"])
            if recording["release_mbid"] or listen["release_mbid"]:
                release_mbids.add(recording["release_mbid"] or listen["release_mbid"])
        else:
            artist_mbids.update(listen["artist_credit_mbids"])
            if listen["release_mbid"]:
                release_mbids.add(listen["release_mbid"])

    artist_metadata = lookup_artist_metadata(client, artist_mbids)
    release_metadata = lookup_release_metadata(client, release_mbids)

    prepared_rows = []
    fallback_artist_pairs = set()
    for listen, submitted_ids in zip(listens, submitted_ids_by_listen):
        recording = recording_metadata.get(listen["recording_mbid"])
        recording_id = submitted_ids["submitted_recording_id"]
        artist_name = listen["artist_name"]
        artist_credit_mbids = listen["artist_credit_mbids"]
        release_name = listen["release_name"]
        release_mbid = listen["release_mbid"]

        if recording is not None and recording["recording_id"] != 0:
            recording_id = recording["recording_id"]
            artist_name = recording["artist_name"] or artist_name
            artist_credit_mbids = recording["artist_credit_mbids"] or artist_credit_mbids
            release_name = recording["release_name"] or release_name
            release_mbid = recording["release_mbid"] or release_mbid

        release = release_metadata.get(release_mbid)
        release_group_id = submitted_ids["submitted_release_group_id"]
        if release is not None and release["release_group_id"] != 0:
            release_group_id = release["release_group_id"]

        artist_credit_mbids = artist_credit_mbids or [""]
        for artist_mbid in artist_credit_mbids:
            artist = artist_metadata.get(artist_mbid)
            if artist is None or artist["artist_id"] == 0:
                fallback_artist_pairs.add((artist_mbid, artist_name))

        prepared_rows.append({
            "listen": listen,
            "submitted_ids": submitted_ids,
            "recording_id": recording_id,
            "artist_name": artist_name,
            "artist_credit_mbids": artist_credit_mbids,
            "release_group_id": release_group_id,
        })

    fallback_artist_ids = calculate_submitted_artist_ids(client, fallback_artist_pairs)

    listen_rows = []
    metadata_rows = {table_name: [] for table_name in METADATA_COLUMNS}

    for row in prepared_rows:
        listen = row["listen"]
        submitted_ids = row["submitted_ids"]
        submitted_rows = build_submitted_metadata_rows(listen, submitted_ids)
        artist_ids, artist_rows = _resolve_artist_ids(
            row["artist_name"],
            row["artist_credit_mbids"],
            fallback_artist_ids,
            artist_metadata,
        )

        if row["recording_id"] == submitted_ids["submitted_recording_id"]:
            metadata_rows["recording_metadata"].extend(submitted_rows["recording_metadata"])
        if row["release_group_id"] == submitted_ids["submitted_release_group_id"]:
            metadata_rows["release_group_metadata"].extend(submitted_rows["release_group_metadata"])
        metadata_rows["artist_metadata"].extend(artist_rows)

        listen_rows.append([
            listen["listened_at"],
            listen["created"],
            listen["user_id"],
            listen["recording_msid"],
            submitted_ids["submitted_recording_id"],
            row["recording_id"],
            submitted_ids["submitted_release_group_id"],
            row["release_group_id"],
            submitted_ids["submitted_artist_ids"],
            artist_ids,
        ])

    return listen_rows, metadata_rows


def transform_arrow_table(table: pa.Table, client: Client) -> tuple[pa.Table, dict[str, list[tuple]]]:
    """Transform Arrow rows using ClickHouse metadata lookups only."""
    listen_rows, metadata_rows = transform_listen_rows(
        [_normalise_listen_row(row) for row in table.to_pandas().to_dict("records")],
        client,
    )

    listen_table = pa.table(
        {col: [row[index] for row in listen_rows] for index, col in enumerate(LISTEN_COLUMNS)}
    )
    return listen_table, metadata_rows


def insert_metadata_rows(client: Client, metadata_rows: dict[str, list[tuple]]) -> None:
    for table_name, rows in dedupe_metadata_rows(metadata_rows).items():
        if rows:
            client.insert(table_name, rows, column_names=METADATA_COLUMNS[table_name])


# =============================================================================
# Parquet file loading
# =============================================================================

def _load_parquet_file(
    file_path: Path,
    host: str, port: int, username: str, password: str, database: str,
    progress: LoadProgress = None,
    batch_size: int = 100_000,
) -> int:
    client = create_client(host, port, username, password, database)
    try:
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows
        if total_rows == 0:
            return 0

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            listen_table, metadata_rows = transform_arrow_table(pa.Table.from_batches([batch]), client)
            client.insert_arrow(
                table=LISTENS_TABLE,
                arrow_table=listen_table,
            )
            insert_metadata_rows(client, metadata_rows)

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
        logger.info("Waiting for async inserts to complete...")
        time.sleep(2)
        verify_client = create_client(host, port, username, password, database)
        count = verify_client.query("SELECT count(*) FROM listens").first_row[0]
        logger.info("Total rows in table: %s", f"{count:,}")
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
