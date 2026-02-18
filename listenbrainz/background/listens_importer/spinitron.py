import csv
from datetime import datetime, timezone
from typing import Any, Iterator, TextIO

from dateutil import parser as dateutil_parser
from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.webserver.errors import ImportFailedError


class SpinitronListensImporter(BaseListensImporter):
    """Importer for Spinitron listening history CSV exports."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "Spinitron Archive Importer"

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the Spinitron CSV export file and returns a generator of batches of items.

        Spinitron CSV files have a metadata header block (playlist title, DJ name, etc.)
        followed by a blank line and then the actual data rows with a header line containing
        ``Date-time``, ``Artist``, ``Song``, ``Release``, and ``Label`` columns.
        """
        self._from_date = import_task["from_date"]
        self._to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8") as file:
            header_line = self._read_header_line(file)
            reader = csv.DictReader(file, fieldnames=header_line)
            yield from chunked(reader, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse Spinitron CSV items to a listens batch."""
        listens = []
        for item in batch:
            try:
                datetime_str = (item.get("date-time") or "").strip()
                if not datetime_str:
                    current_app.logger.debug("Missing Date-time in Spinitron item: %s", item)
                    continue

                dt = dateutil_parser.parse(datetime_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts = int(dt.timestamp())
            except (TypeError, ValueError):
                current_app.logger.debug("Invalid Spinitron timestamp in item: %s", item, exc_info=True)
                continue

            if not (self._from_date <= datetime.fromtimestamp(ts, tz=timezone.utc) <= self._to_date):
                continue

            artist = (item.get("artist") or "").strip()
            song = (item.get("song") or "").strip()
            if not artist or not song:
                current_app.logger.debug("Missing artist or song in Spinitron item: %s", item)
                continue

            listen: dict[str, Any] = {
                "listened_at": ts,
                "track_metadata": {
                    "track_name": song,
                    "artist_name": artist,
                },
            }

            release = (item.get("release") or "").strip()
            if release:
                listen["track_metadata"]["release_name"] = release

            additional_info: dict[str, Any] = {
                "submission_client": self.importer_name,
                "music_service": "spinitron.com",
            }

            label = (item.get("label") or "").strip()
            if label:
                additional_info["label"] = label

            listen["track_metadata"]["additional_info"] = additional_info
            listens.append(listen)

        return listens

    @staticmethod
    def _looks_like_header(line: str) -> list[str] | None:
        """Detect the Spinitron data header row.

        Spinitron CSVs have metadata lines at the top followed by a blank line
        and then the header row.  Column names are handled case-insensitively.
        The required columns are ``date-time``, ``artist`` and ``song``.
        """
        maybe_header = [
            column.strip(' "').lower() for column in line.strip().split(",")
        ]
        expected = {"date-time", "artist", "song"}
        if expected.issubset(maybe_header):
            return maybe_header
        return None

    def _read_header_line(self, file: TextIO) -> list[str]:
        """Advance the file pointer past the metadata block until the data header row is located."""
        file.seek(0)
        for line in file:
            if header := self._looks_like_header(line):
                return header

        raise ImportFailedError("Unable to locate Spinitron header row in import file.")
