import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from io import TextIOWrapper
from typing import Any, Iterator
from zipfile import ZipFile

from flask import current_app

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.webserver.errors import ImportFailedError

FILE_SIZE_LIMIT = 524288000  # 500 MB


class ZipBaseListensImporter(BaseListensImporter, ABC):
    """Abstract base class for zip based listens importers."""

    def __init__(self, db_conn, ts_conn):
        super().__init__(db_conn, ts_conn)
        self.file_size_limit = FILE_SIZE_LIMIT

    @abstractmethod
    def filter_zip_file(self, file: str) -> bool:
        """ Whether the file with the given path in the zip archive should be processed. """
        pass

    @abstractmethod
    def process_file_contents(self, contents: TextIOWrapper) -> Iterator[tuple[datetime, Any]]:
        """ Process the contents of a single file in the zip archive. """
        pass

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        with zipfile.ZipFile(import_task["file_path"]) as zf:
            self._validate_zip_file(zf, import_task["id"])
            yield from self._process_zip_file(
                zf,
                import_task["id"],
                import_task["from_date"],
                import_task["to_date"],
            )

    def _process_zip_file(self, zip_file, import_id: int, from_date: datetime, to_date: datetime) -> Iterator[list[dict[str, Any]]]:
        """Common zip file processing logic.
        
        Args:
            zip_file: The ZipFile object to process
            import_id: ID of the import task
            from_date: Only process entries after this date
            to_date: Only process entries before this date
            
        Yields:
            Batches of processed entries
        """
        import_files = []
        for file in zip_file.namelist():
            if self.filter_zip_file(file):
                info = zip_file.getinfo(file)
                self._validate_file_size(info, import_id)
                import_files.append(file)

        for filename in import_files:
            self.update_import_progress_and_status(import_id, "in_progress", f"Importing {filename}")
            with (
                zip_file.open(filename) as file,
                TextIOWrapper(file, encoding="utf-8") as contents
            ):
                batch = []
                for timestamp, item in self.process_file_contents(contents):
                    if item is not None and from_date <= timestamp <= to_date:
                        batch.append(item)
                        if len(batch) >= self.batch_size:
                            yield batch
                            batch = []
                if batch:
                    yield batch

    def _validate_zip_file(self, zip_file: ZipFile, import_id: int) -> None:
        """Validate zip file against potential zip bomb attacks."""
        if len(zip_file.namelist()) > 500:
            self.update_import_progress_and_status(import_id, "failed", "Import failed due to an error")
            current_app.logger.error("Potential zip bomb attack")
            raise ImportFailedError("Import failed!")
            
    def _validate_file_size(self, file_info, import_id: int) -> None:
        """Validate that a single file in the zip is not too large."""
        if file_info.file_size > self.file_size_limit:
            self.update_import_progress_and_status(
                import_id,
                "failed",
                f"File {file_info.filename} is too large. Maximum allowed size is {self.file_size_limit} bytes.",
            )
            raise ImportFailedError(f"File {file_info.filename} is too large")
