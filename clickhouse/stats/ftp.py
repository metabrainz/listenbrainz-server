"""
FTP Dump Downloader for ClickHouse

Downloads listen dumps from the ListenBrainz FTP server for loading into ClickHouse.
"""

import ftplib
import hashlib
import logging
import os
import tempfile
import time
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DumpType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class DumpInvalidException(Exception):
    """Raised when a dump fails validation."""
    pass


class FTPDumpDownloader:
    """Downloads listen dumps from the ListenBrainz FTP server."""

    def __init__(self, ftp_server: str = "ftp.eu.metabrainz.org", ftp_dir: str = "/pub/musicbrainz/listenbrainz/"):
        self.ftp_server = ftp_server
        self.ftp_dir = ftp_dir
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

    def get_listens_filename(self, dump_dir: str) -> str:
        """Get the listens parquet filename from a dump directory."""
        self.connection.cwd(dump_dir)
        files = self.list_dir()

        # Look for the listens parquet archive
        for f in files:
            if 'listens' in f and f.endswith('.tar.zst'):
                return f

        raise ValueError(f"No listens file found in {dump_dir}")

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

        # Get listens filename
        listens_filename = self.get_listens_filename(dump_dir_name)
        logger.info(f"Listens file: {listens_filename}")

        # Download
        dump_path = self.download_dump(listens_filename, download_dir)

        # Return to root
        self.connection.cwd('/')

        return dump_path, dump_id


def download_dump(
    dump_type: str = "full",
    download_dir: str = None,
    ftp_server: str = None,
    ftp_dir: str = None,
) -> tuple[str, int]:
    """
    Convenience function to download a dump.

    Args:
        dump_type: "full" or "incremental"
        download_dir: Directory to save the dump
        ftp_server: FTP server hostname (default: ftp.eu.metabrainz.org)
        ftp_dir: Base directory on FTP (default: /pub/musicbrainz/listenbrainz/)

    Returns:
        Tuple of (path_to_downloaded_file, dump_id)
    """
    # Get config values if not provided
    if ftp_server is None or ftp_dir is None:
        try:
            from clickhouse import config
            ftp_server = ftp_server or getattr(config, 'FTP_SERVER_URI', 'ftp.eu.metabrainz.org')
            ftp_dir = ftp_dir or getattr(config, 'FTP_LISTENS_DIR', '/pub/musicbrainz/listenbrainz/')
        except ImportError:
            ftp_server = ftp_server or 'ftp.eu.metabrainz.org'
            ftp_dir = ftp_dir or '/pub/musicbrainz/listenbrainz/'

    dtype = DumpType.INCREMENTAL if dump_type == "incremental" else DumpType.FULL

    downloader = FTPDumpDownloader(ftp_server, ftp_dir)
    try:
        downloader.connect()
        return downloader.download_latest_dump(dtype, download_dir)
    finally:
        downloader.close()
