"""Downloads Spark parquet listen dumps from the ListenBrainz FTP server."""

import ftplib
import hashlib
import logging
import os
import socket
import time
from enum import Enum

logger = logging.getLogger(__name__)

FTP_TIMEOUT = 300
DOWNLOAD_BLOCK_SIZE = 1 << 20


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

    def __init__(self, ftp_server: str, ftp_dir: str, port: int = ftplib.FTP_PORT):
        self.ftp_server = ftp_server
        self.ftp_dir = ftp_dir
        self.port = port
        self.connection = None

    def connect(self):
        """Connect to FTP server."""
        self.connection = ftplib.FTP(timeout=FTP_TIMEOUT)
        try:
            self.connection.connect(self.ftp_server, self.port)
            # the control connection idles during a download of hours: keep NATs from dropping it
            self.connection.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.connection.login()
            logger.info(f"Connected to FTP server: {self.ftp_server}")
        except Exception as e:
            logger.error(f"Could not connect to FTP server: {e}")
            self.close()
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

    def _dump_type_dir(self, dump_type: DumpType) -> str:
        if dump_type == DumpType.INCREMENTAL:
            return os.path.join(self.ftp_dir, 'incremental/')
        return os.path.join(self.ftp_dir, 'fullexport/')

    def list_dump_directories(self, dump_type: DumpType) -> list[str]:
        """List available dump directories of the specified type."""
        self.connection.cwd(self._dump_type_dir(dump_type))
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

    def _download_file(self, src: str, dest: str) -> str:
        """Download a file from FTP to local path; returns its SHA256 hex digest."""
        digest = hashlib.sha256()

        def write(block):
            f.write(block)
            digest.update(block)

        with open(dest, 'wb') as f:
            try:
                self.connection.retrbinary(f'RETR {src}', write, blocksize=DOWNLOAD_BLOCK_SIZE)
            except ftplib.error_perm as e:
                logger.error(f"Could not download file {src}: {e}")
                raise
        return digest.hexdigest()

    def download_dump(self, filename: str, directory: str) -> str:
        """Download ``filename`` into ``directory`` and verify its SHA256 checksum; returns its path."""
        sha_filename = filename + '.sha256'
        dir_content = self.list_dir()

        if sha_filename not in dir_content:
            raise DumpInvalidException(f"SHA256 checksum file not found for {filename}")

        sha_dest_path = os.path.join(directory, sha_filename)
        self._download_file(sha_filename, sha_dest_path)

        dest_path = os.path.join(directory, filename)
        logger.info(f"Downloading {filename}...")
        t0 = time.monotonic()
        calculated_sha = self._download_file(filename, dest_path)
        elapsed = time.monotonic() - t0
        logger.info(f"Download complete in {elapsed:.1f}s")

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
        """Return (directory name, id) of dump ``dump_id``, or of the latest dump."""
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

    def download_spark_archive(self, dump_type: DumpType, dump_dir_name: str, download_dir: str) -> str:
        """Download the Spark archive of the dump in directory ``dump_dir_name``; returns its path."""
        spark_dump_filename = self.get_spark_dump_filename(dump_dir_name)
        logger.info(f"Spark dump file: {spark_dump_filename}")
        self.connection.cwd(os.path.join(self._dump_type_dir(dump_type), dump_dir_name))
        return self.download_dump(spark_dump_filename, download_dir)


def get_ftp_downloader(app) -> FTPDumpDownloader:
    return FTPDumpDownloader(
        app.config["FTP_SERVER_URI"],
        app.config["FTP_LISTENS_DIR"],
        app.config.get("FTP_SERVER_PORT", ftplib.FTP_PORT)
    )
