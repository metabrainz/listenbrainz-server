import json
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Iterator
from zipfile import ZipFile

from flask import current_app
from sqlalchemy.sql.expression import text
from werkzeug.exceptions import InternalServerError, ServiceUnavailable

from listenbrainz.db import user as db_user
from listenbrainz.domain.external_service import ExternalServiceError
from listenbrainz.webserver.errors import ImportFailedError, ListenValidationError
from listenbrainz.webserver.models import SubmitListenUserMetadata
from listenbrainz.webserver.views.api_tools import insert_payload, LISTEN_TYPE_IMPORT, validate_listen

BATCH_SIZE = 1000
FILE_SIZE_LIMIT = 524288000  # 500 MB
IMPORTER_NAME = "ListenBrainz Archive Importer"


class BaseListensImporter(ABC):
    """Abstract base class for listens importers."""

    def __init__(self, db_conn, ts_conn):
        self.db_conn = db_conn
        self.ts_conn = ts_conn
        self.batch_size = BATCH_SIZE
        self.file_size_limit = FILE_SIZE_LIMIT
        self.importer_name = IMPORTER_NAME

    def import_listens(self, user_id: int, import_task: dict[str, Any]) -> None:
        """Main entry point for importing listens."""
        user = db_user.get(self.db_conn, user_id)
        if user is None:
            current_app.logger.error("User with id: %s does not exist, skipping import.", user_id)
            return

        import_id = import_task["id"]
        metadata = import_task["metadata"]
        if metadata["status"] in {"cancelled", "failed"}:
            return

        self.update_import_progress_and_status(import_id, "in_progress", "Importing user listens")

        try:
            with zipfile.ZipFile(import_task["file_path"]) as zf:
                self._validate_zip_file(zf, import_id)
                for batch in self._process_zip_file(
                    zf,
                    import_id,
                    import_task["from_date"],
                    import_task["to_date"],
                ):
                    parsed_listens = self._parse_listen_batch(batch)

                    validated_listens = []
                    for listen in parsed_listens:
                        try:
                            validate_listen(listen, LISTEN_TYPE_IMPORT)
                            validated_listens.append(listen)
                        except ListenValidationError as e:
                            current_app.logger.error("Invalid listen: %s", e)

                    self.submit_listens(parsed_listens, user_id, user["musicbrainz_id"], import_id)

            self.update_import_progress_and_status(import_id, "completed", "Import completed!")
        except ImportFailedError as e:
            self.update_import_progress_and_status(import_id, "failed", str(e))
        finally:
            Path(import_task["file_path"]).unlink(missing_ok=True)

    @abstractmethod
    def _filter_zip_files(self, file: str) -> bool:
        """ Whether the file with the given path in the zip archive should be processed. """
        pass

    @abstractmethod
    def _process_file_contents(self, contents: TextIOWrapper) -> Iterator[tuple[datetime, Any]]:
        """ Process the contents of a single file in the zip archive. """
        pass

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
            if self._filter_zip_files(file):
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
                for timestamp, item in self._process_file_contents(contents):
                    if item is not None and from_date <= timestamp <= to_date:
                        batch.append(item)
                        if len(batch) >= self.batch_size:
                            yield batch
                            batch = []
                if batch:
                    yield batch

    @abstractmethod
    def _parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse a batch of raw entries into listen format."""
        pass

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

    def submit_listens(self, listens: list[dict[str, Any]], user_id: int, username: str, import_id: int) -> None:
        """Submit parsed listens to the database."""
        if not listens:
            return

        user_metadata = SubmitListenUserMetadata(user_id=user_id, musicbrainz_id=username)
        retries = 10

        while retries >= 0:
            try:
                current_app.logger.debug("Submitting %d listens for user %s", len(listens), username)
                insert_payload(listens, user_metadata, listen_type=LISTEN_TYPE_IMPORT)
                break
            except (InternalServerError, ServiceUnavailable):
                retries -= 1
                current_app.logger.error("ISE while trying to import listens for %s:", username, exc_info=True)
                if retries == 0:
                    self.update_import_progress_and_status(import_id, "failed", "Import failed due to an error")
                    raise ExternalServiceError("ISE while trying to import listens")

    def update_import_progress_and_status(self, import_id: int, status: str, progress: str) -> None:
        """Update progress for user data import."""
        query = text("""
             UPDATE user_data_import
                SET metadata = metadata || (:metadata)::jsonb
              WHERE id = :import_id
        """)
        updated_metadata = {"status": status, "progress": progress}
        self.db_conn.execute(query, {
            "metadata": json.dumps(updated_metadata),
            "import_id": import_id
        })
        self.db_conn.commit()
