"""
FTP Dump Downloader for ClickHouse

Downloads Spark parquet listen dumps from the ListenBrainz FTP server for loading into ClickHouse.
"""

import ftplib
import hashlib
import logging
import os
import tempfile
import time
from enum import Enum
from pathlib import Path

from clickhouse import config

logger = logging.getLogger(__name__)


class DumpType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class DumpInvalidException(Exception):
    """Raised when a dump fails validation."""
    pass


class FTPDumpDownloader:
    """Downloads Spark parquet listen dumps from the ListenBrainz FTP server."""

    def __init__(self):
        self.ftp_server = config.FTP_SERVER_URI
        self.ftp_dir = config.FTP_LISTENS_DIR
        self.connection = None

    def connect(self):
        """Connect to FTP server."""
        try:
            self.connection = ftplib.FTP(self.ftp_server)
            self.connection.login()
            logger.info(f"Connected to FTP server: {self.ftp_server}")
        except ftplib.error_perm as e:
            logger.critical(f"Could not connect to FTP server: {e}")
            raise

    def close(self):
        """Close FTP connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def list_dir(self, path: str = None) -> list[str]:
        """List contents of a directory on FTP server."""
        files = []
        cmd = 'NLST'
        if path:
            cmd += ' ' + path
        self.connection.retrlines(cmd, callback=files.append)
        return files

    def list_dump_directories(self, dump_type: DumpType) -> list[str]:
        """List available dump directories of the specified type."""
        if dump_type == DumpType.INCREMENTAL:
            dump_dir = os.path.join(self.ftp_dir, 'incremental/')
        else:
            dump_dir = os.path.join(self.ftp_dir, 'fullexport/')

        self.connection.cwd(dump_dir)
        return self.list_dir()

    def _download_file(self, src: str, dest: str):
        """Download a file from FTP to local path."""
        with open(dest, 'wb') as f:
            try:
                self.connection.retrbinary(f'RETR {src}', f.write)
            except ftplib.error_perm as e:
                logger.error(f"Could not download file {src}: {e}")
                raise

    def _calc_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _read_sha_file(self, sha_path: str) -> str:
        """Read SHA256 checksum from a .sha256 file."""
        with open(sha_path, 'r') as f:
            return f.read().split()[0].strip()

    def download_dump(self, filename: str, directory: str) -> str:
        """
        Download and validate a dump file from FTP.

        Args:
            filename: Name of the dump file to download
            directory: Local directory to save the file

        Returns:
            Path to the downloaded file

        Raises:
            DumpInvalidException: If checksum validation fails
        """
        # Check for SHA256 file
        sha_filename = filename + '.sha256'
        dir_content = self.list_dir()

        if sha_filename not in dir_content:
            raise DumpInvalidException(f"SHA256 checksum file not found for {filename}")

        # Download SHA256 file
        sha_dest_path = os.path.join(directory, sha_filename)
        self._download_file(sha_filename, sha_dest_path)

        # Download dump file
        dest_path = os.path.join(directory, filename)
        logger.info(f"Downloading {filename}...")
        t0 = time.monotonic()
        self._download_file(filename, dest_path)
        elapsed = time.monotonic() - t0
        logger.info(f"Download complete in {elapsed:.1f}s")

        # Verify checksum
        logger.info("Verifying dump integrity...")
        calculated_sha = self._calc_sha256(dest_path)
        received_sha = self._read_sha_file(sha_dest_path)

        os.remove(sha_dest_path)

        if calculated_sha != received_sha:
            os.remove(dest_path)
            raise DumpInvalidException(
                f"SHA256 mismatch: calculated={calculated_sha[:16]}..., expected={received_sha[:16]}..."
            )

        logger.info("Checksum verified successfully")
        return dest_path

    def get_latest_dump_name(self, dump_type: DumpType) -> tuple[str, int]:
        """
        Get the name and ID of the latest available dump.

        Returns:
            Tuple of (dump_directory_name, dump_id)
        """
        dump_dirs = self.list_dump_directories(dump_type)
        # Sort by dump ID (format: listenbrainz-dump-XXXX-...)
        sorted_dirs = sorted(dump_dirs, key=lambda x: int(x.split('-')[2]) if len(x.split('-')) > 2 else 0)
        if not sorted_dirs:
            raise ValueError(f"No {dump_type.value} dumps found on FTP server")

        latest = sorted_dirs[-1]
        dump_id = int(latest.split('-')[2])
        return latest, dump_id

    def get_spark_dump_filename(self, dump_dir: str) -> str:
        """Get the Spark parquet archive filename for a ListenBrainz dump directory."""
        parts = dump_dir.rstrip("/").split("-")
        if len(parts) < 6:
            raise ValueError(f"Invalid dump directory name: {dump_dir}")
        return f"listenbrainz-spark-dump-{parts[2]}-{parts[3]}-{parts[4]}-{parts[5]}.tar"

    def download_latest_dump(
        self,
        dump_type: DumpType = DumpType.FULL,
        download_dir: str = None,
    ) -> tuple[str, int]:
        """
        Download the latest dump from FTP.

        Args:
            dump_type: Type of dump (FULL or INCREMENTAL)
            download_dir: Directory to save the dump (uses temp dir if not specified)

        Returns:
            Tuple of (path_to_downloaded_file, dump_id)
        """
        if download_dir is None:
            download_dir = tempfile.mkdtemp(prefix="clickhouse_dump_")

        Path(download_dir).mkdir(parents=True, exist_ok=True)

        # Get latest dump info
        dump_dir_name, dump_id = self.get_latest_dump_name(dump_type)
        logger.info(f"Latest {dump_type.value} dump: {dump_dir_name} (ID: {dump_id})")

        spark_dump_filename = self.get_spark_dump_filename(dump_dir_name)
        logger.info(f"Spark dump file: {spark_dump_filename}")

        self.connection.cwd(dump_dir_name)
        dump_path = self.download_dump(spark_dump_filename, download_dir)

        # Return to root
        self.connection.cwd('/')

        return dump_path, dump_id
