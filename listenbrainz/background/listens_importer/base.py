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
        """Main entry point for importing listens.

        Retrieves import task from database, processes the import file, parses the items into
        listens, validates them and submits them to the database.

        Args:
            user_id: the user whose listens are to be submitted
            import_task: the import task dict
        """
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
            validation_stats = self._initialize_validation_stats()
            self.persist_validation_stats(import_id, validation_stats)
            for batch in self.process_import_file(import_task):
                validated_listens, validation_stats = self.parse_and_validate_listen_items(
                    batch,
                    validation_stats,
                )

                self.submit_listens(validated_listens, user_id, user["musicbrainz_id"], import_id)
                self.persist_validation_stats(import_id, validation_stats)

            self.update_import_progress_and_status(import_id, "completed", "Import completed!")
        except Exception as e:
            self.update_import_progress_and_status(import_id, "failed", str(e))
        finally:
            Path(import_task["file_path"]).unlink(missing_ok=True)

    @abstractmethod
    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Process the service specific import file.

        Args:
            import_task: the import task dict

        Returns: iterator of batches of raw entries from service import file
        """
        pass

    @abstractmethod
    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse a batch of raw entries into listen format.

        Args:
            batch: a list of raw entries from service import file

        Returns: a list of parsed listens
        """
        pass

    def submit_listens(self, listens: list[dict[str, Any]], user_id: int, username: str, import_id: int) -> None:
        """Submit parsed listens to the database.

        Args:
            listens: a batch of parsed listens
            user_id: the user whose listens are to be submitted
            username: the user's musicbrainz username
            import_id: the import task ID
        """
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

    @staticmethod
    def _initialize_validation_stats() -> dict[str, int]:
        """Return a fresh attempted/success counter dict."""
        return {"attempted_count": 0, "success_count": 0}

    def parse_and_validate_listen_items(
        self,
        batch: list[dict[str, Any]],
        validation_stats: dict[str, int],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Parse raw entries and validate them while updating counters."""
        raw_attempts = len(batch)
        parsed_listens = self.parse_listen_batch(batch)
        parsed_count = len(parsed_listens)
        dropped_during_parsing = raw_attempts - parsed_count

        if dropped_during_parsing > 0:
            current_app.logger.warning(
                "Dropped %d listens during parsing in %s importer", dropped_during_parsing, self.importer_name
            )

        validation_stats["attempted_count"] += raw_attempts

        validated_listens: list[dict[str, Any]] = []
        for listen in parsed_listens:
            try:
                validate_listen(listen, LISTEN_TYPE_IMPORT)
                validated_listens.append(listen)
            except ListenValidationError as e:
                current_app.logger.error("Invalid listen: %s", e)
        
        validation_stats["success_count"] = len(validated_listens)

        return validated_listens, validation_stats

    def persist_validation_stats(self, import_id: int, validation_stats: dict[str, int]) -> None:
        """Persist the current validation counters on the import task metadata."""
        self._merge_import_metadata(import_id, {
            "attempted_count": validation_stats.get("attempted_count", 0),
            "success_count": validation_stats.get("success_count", 0),
        })

    def update_import_progress_and_status(self, import_id: int, status: str, progress: str) -> None:
        """Update progress for user data import."""
        updated_metadata = {"status": status, "progress": progress}
        self._merge_import_metadata(import_id, updated_metadata)

    def _merge_import_metadata(self, import_id: int, metadata_updates: dict[str, Any]) -> None:
        """Merge arbitrary metadata fields into user_data_import.metadata."""
        if not metadata_updates:
            return

        query = text("""
             UPDATE user_data_import
                SET metadata = metadata || (:metadata)::jsonb
              WHERE id = :import_id
        """)
        self.db_conn.execute(query, {
            "metadata": json.dumps(metadata_updates),
            "import_id": import_id
        })
        self.db_conn.commit()
