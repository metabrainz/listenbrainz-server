import csv
from datetime import datetime, timezone
from typing import Any, Iterator, TextIO

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.webserver.errors import ImportFailedError


class LibrefmListensImporter(BaseListensImporter):
    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the libre.fm csv archive file and returns a generator of batches of items."""

        self._from_date = import_task["from_date"]
        self._to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8") as file:
            header_line = self._read_header_line(file)
            reader = csv.DictReader(file, fieldnames=header_line)
            yield from chunked(reader, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse libre.fm items to a listens batch."""
        listens = []
        for item in batch:
            try:
                ts = int(item["time"])
            except (TypeError, ValueError):
                current_app.logger.error("Invalid Libre.fm timestamp in item: %s", item, exc_info=True)
                continue
            if not (self._from_date <= datetime.fromtimestamp(ts, tz=timezone.utc) <= self._to_date):
                continue
            listen = {
                "listened_at": item["time"],
                "track_metadata": {
                    "track_name": item["track"],
                    "artist_name": item["artist"],
                }
            }
            if item.get("album"):
                listen["track_metadata"]["release_name"] = item["album"]
            listen["track_metadata"]["additional_info"] = {
                "submission_client": self.importer_name,
                "music_service": "libre.fm"
            }
            listens.append(listen)
        return listens

    @staticmethod
    def _looks_like_header(line: str) -> list[str] | None:
        """Skip comment lines and find the first header line. Column names need
           to be handled case-insensitively. Extra columns (userid) are allowed
           but need to be included in the header for DictReader to ignore them.
        """
        maybe_header = [
            column.strip(' "').lower() for column in line.strip().split(",")
        ]
        expected = {"time", "artist", "track"}
        if expected.issubset(maybe_header):
            return maybe_header
        return None

    def _read_header_line(self, file: TextIO) -> list[str]:
        """Advance the file pointer until a header row is located."""
        file.seek(0)
        for line in file:
            if header := self._looks_like_header(line):
                return header

        raise ImportFailedError("Unable to locate Libre.fm header row in import file.")