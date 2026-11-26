"""A real FTP server serving dumps laid out like the ListenBrainz FTP server."""

import hashlib
import io
from datetime import datetime, timedelta, timezone
import tarfile
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

from listenbrainz.clickhouse.query_worker.listens.ftp import DumpType, FTPDumpDownloader
from listenbrainz.clickhouse.query_worker.tests import TEST_DATA_PATH

LISTENS_DIR = "/listens/"


def dump_dir_name(dump_id: int, dump_type: DumpType | str) -> str:
    kind = dump_type.value if isinstance(dump_type, DumpType) else dump_type
    return f"listenbrainz-dump-{dump_id}-20260101-000000-{kind}"


class DumpFTPServer:
    """Serves a temporary directory over FTP to anonymous users until the test ends."""

    def __init__(self, test):
        root = TemporaryDirectory()
        # registered first, so it runs after the server stops
        test.addCleanup(root.cleanup)
        self.root = Path(root.name)
        # a subclass, so each server has its own authorizer
        class Handler(FTPHandler):
            authorizer = DummyAuthorizer()
            authorizer.add_anonymous(root.name)

        self.server = FTPServer(("127.0.0.1", 0), Handler)
        stop = threading.Event()

        def serve():
            while not stop.is_set():
                self.server.serve_forever(timeout=0.05, blocking=False, handle_exit=False)
            self.server.close_all()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        test.addCleanup(thread.join)
        test.addCleanup(stop.set)

    def downloader(self) -> FTPDumpDownloader:
        host, port = self.server.address
        return FTPDumpDownloader(host, LISTENS_DIR, port)

    def dump_dir(self, dump_type: DumpType) -> Path:
        directory = self.root / LISTENS_DIR.strip("/") / ("fullexport" if dump_type == DumpType.FULL else "incremental")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def add_dump(self, dump_id: int, dump_type: DumpType, fixture: str | None, checksum: str | None = "valid",
                 coverage_day: int | None = None) -> Path:
        """Publish fixture ``fixture`` (None: no listens) as dump ``dump_id``: its Spark archive
        and, unless ``checksum`` is None, a checksum file ("valid" or a wrong one otherwise)."""
        name = dump_dir_name(dump_id, dump_type)
        directory = self.dump_dir(dump_type) / name
        directory.mkdir()
        archive = directory / f"listenbrainz-spark-dump-{dump_id}-20260101-000000-{dump_type.value}.tar"
        with tarfile.open(archive, "w") as tar:
            if fixture is not None:
                tar.add(
                    TEST_DATA_PATH / fixture, arcname=archive.name.removesuffix(".tar"),
                    filter=lambda member: None if Path(member.name).name in {
                        "TIMESTAMP", "START_TIMESTAMP", "END_TIMESTAMP"
                    } else member,
                )
            epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
            coverage_day = dump_id if coverage_day is None else coverage_day
            metadata = {"TIMESTAMP": epoch + timedelta(days=coverage_day)} if dump_type == DumpType.FULL else {
                "START_TIMESTAMP": epoch + timedelta(days=coverage_day - 1),
                "END_TIMESTAMP": epoch + timedelta(days=coverage_day),
            }
            for key, value in metadata.items():
                data = value.isoformat(" ").encode()
                member = tarfile.TarInfo(f"{archive.stem}/{key}")
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
        if checksum is not None:
            digest = hashlib.sha256(archive.read_bytes()).hexdigest() if checksum == "valid" else "0" * 64
            (directory / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n")
        return archive
