import csv
from datetime import datetime, timezone
from typing import Any, Iterator, TextIO

from flask import current_app
from more_itertools import chunked
from dateutil import parser as dateutil_parser

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.webserver.errors import ImportFailedError


class TidalListensImporter(BaseListensImporter):
    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the Tidal streaming.csv file and returns a generator of batches of items."""
        self._from_date = import_task["from_date"]
        self._to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8") as file:
            header_line = self._read_header_line(file)
            reader = csv.DictReader(file, fieldnames=header_line)
            yield from chunked(reader, self.batch_size)
    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse Tidal's streaming.csv file into a listens batch"""
        listens = []
        for item in batch:
            try:
                date_time = datetime.strptime(item["entry_date"], "%d/%m/%y %H:%M") # TODO: Do we use the timezone column of the streaming csv file to append info about the timezone?
                ts = int(date_time.timestamp())
            except (TypeError, ValueError):
                current_app.logger.debug("Invalid Timestamp in item: %s", item, exc_info=True)
                continue

            if not (self._from_date <= datetime.fromtimestamp <= self._to_date):
                continue

            artist_name = item["artist_name"]
            track_title = item["track_title"]

            listen: dict[str, Any] = {
                "listened_at": ts,
                "track_metadata": {
                    "track_name": track_title,
                    "artist_name": artist_name
                },
            }

            additional_info: dict[str, Any] = {
                "submission_client": self.importer_name,
                "original_submission_client": "Tidal",
            }

            listen["track_metadata"]["additional_info"] = additional_info
            listens.append(listen)
        return listens

    @staticmethod
    def _looks_like_header(line: str) -> list[str] | None:
        maybe_header = [
            column.strip(' "').lower() for column in line.strip().split(",")
        ]
        expected = {"artist_name", "track_title", "entry_date"}
        if expected.issubset(maybe_header):
            return maybe_header
        return None

    def _read_header_line(self, file: TextIO) -> list[str]:
        file.seek(0)
        for line in file:
            header = self._looks_like_header(line)
            if header:
                return header
        raise ImportFailedError("Could not find Tidal header row in streaming file.")
 
            
