"""
FTP Dump Downloader for ClickHouse

Downloads Spark parquet listen dumps from the ListenBrainz FTP server for loading into ClickHouse.
"""

import ftplib
import hashlib
import logging
import os
import time
from enum import Enum

from clickhouse import config

logger = logging.getLogger(__name__)


class DumpType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class DumpInvalidException(Exception):
    """Raised when a dump fails validation."""
    pass


class DumpNotFoundException(Exception):
    """Raised when a requested dump id is not available on the FTP server."""
    pass


def _dump_name_parts(name: str) -> list[str]:
    """Split a ``listenbrainz-dump-{id}-{date}-{tod}-{type}`` directory name."""
    parts = name.rstrip('/').split('-')
    if len(parts) < 6:
        raise ValueError(f"Invalid dump directory name: {name}")
    return parts


def parse_dump_id(name: str) -> int:
    """Return the dump id of a ``listenbrainz-dump-{id}-{date}-{tod}-{type}`` directory name."""
    return int(_dump_name_parts(name)[2])


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

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc_info):
        self.close()

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
        directories = self.list_dir()
        if dump_type == DumpType.FULL:
            # fullexport/ also holds the database dumps, which contain no listens
            directories = [d for d in directories if not d.rstrip('/').endswith('-db')]
        return directories

    def list_dump_ids(self, dump_type: DumpType) -> list[tuple[int, str]]:
        """List (dump_id, directory name) for every available dump, oldest first."""
        dumps = []
        for name in self.list_dump_directories(dump_type):
            try:
                dumps.append((parse_dump_id(name), name))
            except ValueError:
                logger.warning("Skipping unrecognised dump directory: %s", name)
        dumps.sort(key=lambda dump: dump[0])
        return dumps

    def _download_file(self, src: str, dest: str):
        """Download a file from FTP to local path."""
        with open(dest, 'wb') as f:
            try:
                self.connection.retrbinary(f'RETR {src}', f.write)
            except ftplib.error_perm as e:
                logger.error(f"Could not download file {src}: {e}")
                raise

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
        with open(dest_path, 'rb') as f:
            calculated_sha = hashlib.file_digest(f, 'sha256').hexdigest()
        with open(sha_dest_path) as f:
            received_sha = f.read().split()[0]

        os.remove(sha_dest_path)

        if calculated_sha != received_sha:
            os.remove(dest_path)
            raise DumpInvalidException(
                f"SHA256 mismatch: calculated={calculated_sha[:16]}..., expected={received_sha[:16]}..."
            )

        logger.info("Checksum verified successfully")
        return dest_path

    def get_dump_name(self, dump_type: DumpType, dump_id: int = None) -> tuple[str, int]:
        """
        Get the name and ID of the dump to download.

        Args:
            dump_type: FULL or INCREMENTAL.
            dump_id: Specific dump ID to look for; defaults to the latest available.

        Returns:
            Tuple of (dump_directory_name, dump_id)
        """
        dumps = self.list_dump_ids(dump_type)
        if not dumps:
            raise ValueError(f"No {dump_type.value} dumps found on FTP server")

        if dump_id is None:
            return dumps[-1][1], dumps[-1][0]

        for found_id, name in dumps:
            if found_id == dump_id:
                return name, found_id
        raise DumpNotFoundException(f"{dump_type.value} dump {dump_id} not found on FTP server")

    def get_spark_dump_filename(self, dump_dir: str) -> str:
        """Get the Spark parquet archive filename for a ListenBrainz dump directory."""
        parts = _dump_name_parts(dump_dir)
        return f"listenbrainz-spark-dump-{parts[2]}-{parts[3]}-{parts[4]}-{parts[5]}.tar"

    def download_dump_archive(
        self,
        dump_type: DumpType,
        download_dir: str,
        dump_id: int = None,
    ) -> tuple[str, int]:
        """
        Download a dump from FTP.

        Args:
            dump_type: Type of dump (FULL or INCREMENTAL)
            download_dir: Existing directory to save the dump in
            dump_id: Specific dump ID to download; defaults to the latest available.

        Returns:
            Tuple of (path_to_downloaded_file, dump_id)
        """
        dump_dir_name, dump_id = self.get_dump_name(dump_type, dump_id)
        logger.info(f"Selected {dump_type.value} dump: {dump_dir_name} (ID: {dump_id})")

        spark_dump_filename = self.get_spark_dump_filename(dump_dir_name)
        logger.info(f"Spark dump file: {spark_dump_filename}")

        self.connection.cwd(dump_dir_name)
        dump_path = self.download_dump(spark_dump_filename, download_dir)

        # Return to root
        self.connection.cwd('/')

        return dump_path, dump_id
