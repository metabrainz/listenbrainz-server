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
            for batch in self.process_import_file(import_task):
                parsed_listens = self.parse_listen_batch(batch)

                validated_listens = []
                for listen in parsed_listens:
                    try:
                        validate_listen(listen, LISTEN_TYPE_IMPORT)
                        validated_listens.append(listen)
                    except ListenValidationError as e:
                        current_app.logger.error("Invalid listen: %s", e)

                self.submit_listens(parsed_listens, user_id, user["musicbrainz_id"], import_id)

            self.update_import_progress_and_status(import_id, "completed", "Import completed!")
        except Exception as e:
            self.update_import_progress_and_status(import_id, "failed", str(e))
        finally:
            Path(import_task["file_path"]).unlink(missing_ok=True)

    @abstractmethod
    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Process the import file."""
        pass

    @abstractmethod
    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse a batch of raw entries into listen format."""
        pass

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
