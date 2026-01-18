#!/usr/bin/env python3
"""
Load Parquet files into ClickHouse listens table.

This module provides functions for loading Parquet dumps into ClickHouse
using parallel processing with Arrow or Pandas.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import clickhouse_connect
from clickhouse_connect.driver import Client
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

logger = logging.getLogger(__name__)

COLUMNS = [
    "listened_at",
    "created",
    "user_id",
    "recording_msid",
    "artist_name",
    "artist_credit_id",
    "release_name",
    "release_mbid",
    "recording_name",
    "recording_mbid",
    "artist_credit_mbids",
    "artist_mb_ids",
    "is_mapped",
]


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


def create_client(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
) -> Client:
    """Create a new ClickHouse client connection."""
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        compress=False,
        settings={
            "async_insert": 1,
            "wait_for_async_insert": 0,
        },
    )


def transform_arrow_table(table: pa.Table) -> pa.Table:
    """
    Transform Arrow table to match ClickHouse schema.
    Uses vectorized PyArrow operations.
    """
    new_columns = {}

    new_columns["listened_at"] = table.column("listened_at")
    new_columns["created"] = table.column("created")
    new_columns["user_id"] = table.column("user_id").cast(pa.uint32())

    for col in ["recording_msid", "artist_name", "recording_name"]:
        arr = table.column(col)
        new_columns[col] = pc.if_else(pc.is_null(arr), "", arr)

    for col in ["release_name", "release_mbid", "recording_mbid"]:
        arr = table.column(col)
        new_columns[col] = pc.if_else(pc.is_null(arr), "", arr)

    arr = table.column("artist_credit_id")
    new_columns["artist_credit_id"] = pc.if_else(
        pc.is_null(arr),
        pa.scalar(0, type=pa.uint64()),
        arr.cast(pa.uint64())
    )

    arr = table.column("artist_credit_mbids")
    mbids_series = arr.to_pandas()
    clean_mbids = mbids_series.apply(
        lambda x: [v for v in x if v is not None] if x is not None else []
    )
    new_columns["artist_credit_mbids"] = pa.array(clean_mbids.tolist(), type=pa.list_(pa.string()))

    # artist_mb_ids - MB integer artist IDs (may not exist in older dumps)
    if "artist_mb_ids" in table.column_names:
        arr = table.column("artist_mb_ids")
        ids_series = arr.to_pandas()
        clean_ids = ids_series.apply(
            lambda x: [v for v in x if v is not None] if x is not None else []
        )
        new_columns["artist_mb_ids"] = pa.array(clean_ids.tolist(), type=pa.list_(pa.uint32()))
    else:
        # Default to empty arrays for older dumps
        new_columns["artist_mb_ids"] = pa.array(
            [[] for _ in range(table.num_rows)], type=pa.list_(pa.uint32())
        )

    # is_mapped - whether listen uses MB mapping data (may not exist in older dumps)
    if "is_mapped" in table.column_names:
        new_columns["is_mapped"] = table.column("is_mapped")
    else:
        # Default to False for older dumps (will be computed based on artist_credit_id > 0)
        # Actually, infer from artist_credit_id: mapped if artist_credit_id > 0
        new_columns["is_mapped"] = pc.greater(new_columns["artist_credit_id"], pa.scalar(0, type=pa.uint64()))

    return pa.table({col: new_columns[col] for col in COLUMNS})


def load_parquet_file_arrow(
    file_path: Path,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    progress: LoadProgress = None,
    batch_size: int = 100_000,
) -> int:
    """
    Load a single parquet file into ClickHouse using Arrow with batch iteration.

    Uses iter_batches to avoid loading entire file into memory at once.
    """
    client = create_client(host, port, username, password, database)

    try:
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows

        if total_rows == 0:
            return 0

        rows_loaded = 0
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            table = pa.Table.from_batches([batch])
            transformed = transform_arrow_table(table)

            client.insert_arrow(
                table="listens",
                arrow_table=transformed,
            )
            rows_loaded += batch.num_rows

        if progress:
            progress.update(total_rows)

        return total_rows

    finally:
        client.close()


def load_parquet_file_pandas(
    file_path: Path,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
    progress: LoadProgress = None,
    batch_size: int = 100_000,
) -> int:
    """
    Fallback: Load using pandas DataFrame insert with batch iteration.

    Uses iter_batches to avoid loading entire file into memory at once.
    """
    client = create_client(host, port, username, password, database)

    try:
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows

        if total_rows == 0:
            return 0

        def fix_array(val):
            if val is None:
                return []
            if hasattr(val, 'tolist'):
                val = val.tolist()
            return [v for v in val if v is not None] if val else []

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            df = batch.to_pandas()

            df["user_id"] = df["user_id"].astype("uint32")
            df["recording_msid"] = df["recording_msid"].fillna("")
            df["artist_name"] = df["artist_name"].fillna("")
            df["recording_name"] = df["recording_name"].fillna("")

            df["artist_credit_id"] = df["artist_credit_id"].fillna(0).astype("uint64")
            df["release_name"] = df["release_name"].fillna("")
            df["release_mbid"] = df["release_mbid"].fillna("")
            df["recording_mbid"] = df["recording_mbid"].fillna("")

            df["artist_credit_mbids"] = df["artist_credit_mbids"].apply(fix_array)

            # artist_mb_ids - MB integer artist IDs (may not exist in older dumps)
            if "artist_mb_ids" in df.columns:
                df["artist_mb_ids"] = df["artist_mb_ids"].apply(fix_array)
            else:
                df["artist_mb_ids"] = [[] for _ in range(len(df))]

            # is_mapped - whether listen uses MB mapping data (may not exist in older dumps)
            if "is_mapped" in df.columns:
                df["is_mapped"] = df["is_mapped"].fillna(False).astype(bool)
            else:
                # Infer from artist_credit_id: mapped if artist_credit_id > 0
                df["is_mapped"] = df["artist_credit_id"] > 0

            client.insert_df(
                table="listens",
                df=df[COLUMNS],
            )

        if progress:
            progress.update(total_rows)

        return total_rows

    finally:
        client.close()


def find_parquet_files(directory: Path) -> list[Path]:
    """Recursively find all parquet files in directory."""
    files = list(directory.rglob("*.parquet"))
    files.sort()
    return files


def load_dump(
    directory: str,
    host: str = "localhost",
    port: int = 8123,
    username: str = "default",
    password: str = "",
    database: str = "default",
    workers: int = 4,
    use_arrow: bool = True,
) -> dict:
    """
    Load Parquet dump files into ClickHouse.

    Args:
        directory: Path to directory containing Parquet files
        host: ClickHouse host
        port: ClickHouse port
        username: ClickHouse username
        password: ClickHouse password
        database: ClickHouse database
        workers: Number of parallel workers
        use_arrow: Use Arrow (True) or Pandas (False) for loading

    Returns:
        Dict with 'total_inserted', 'files_completed', 'elapsed', 'errors'
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    parquet_files = find_parquet_files(dir_path)

    if not parquet_files:
        logger.info(f"No parquet files found in {directory}")
        return {
            'total_inserted': 0,
            'files_completed': 0,
            'elapsed': 0,
            'errors': [],
        }

    logger.info(f"Found {len(parquet_files)} parquet files")
    logger.info(f"Using {workers} parallel workers")
    logger.info(f"Insert mode: {'Arrow' if use_arrow else 'Pandas DataFrame'}")

    # Test connection
    test_client = create_client(host, port, username, password, database)
    logger.info(f"Connected to ClickHouse at {host}:{port}")
    test_client.close()

    load_fn = load_parquet_file_arrow if use_arrow else load_parquet_file_pandas
    progress = LoadProgress()

    start_time = time.time()
    errors = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                load_fn,
                file_path,
                host, port, username, password, database,
                progress
            ): file_path
            for file_path in parquet_files
        }

        for future in as_completed(futures):
            file_path = futures[future]
            try:
                future.result()
                total, completed = progress.get()
                elapsed = time.time() - start_time
                rate = total / elapsed if elapsed > 0 else 0
                logger.info(
                    f"[{completed}/{len(parquet_files)}] "
                    f"{total:,} rows | {rate:,.0f} rows/sec"
                )
            except Exception as e:
                errors.append((str(file_path), str(e)))
                logger.error(f"Error loading {file_path}: {e}")

    elapsed = time.time() - start_time
    total_inserted, files_completed = progress.get()

    logger.info(f"Completed in {elapsed:.1f} seconds")
    logger.info(f"Total rows inserted: {total_inserted:,}")
    if elapsed > 0:
        logger.info(f"Average rate: {total_inserted / elapsed:,.0f} rows/sec")

    if errors:
        logger.error(f"Errors ({len(errors)}):")
        for path, error in errors[:10]:
            logger.error(f"  {path}: {error}")

    # Verify count
    if total_inserted > 0:
        logger.info("Waiting for async inserts to complete...")
        time.sleep(2)

        verify_client = create_client(host, port, username, password, database)
        result = verify_client.query("SELECT count(*) FROM listens")
        logger.info(f"Total rows in table: {result.first_row[0]:,}")
        verify_client.close()

    return {
        'total_inserted': total_inserted,
        'files_completed': files_completed,
        'elapsed': elapsed,
        'errors': errors,
    }
