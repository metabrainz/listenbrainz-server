import csv
from datetime import datetime, timezone
from typing import Any, Iterator, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.webserver.errors import ImportFailedError


class TidalListensImporter(BaseListensImporter):
    DEFAULT_TIMEZONE = timezone.utc

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the Tidal streaming.csv file and returns a generator of batches of items."""
        from_date = import_task["from_date"]
        to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8-sig") as file:
            header_line = self._read_header_line(file)
            reader = csv.DictReader(file, fieldnames=header_line)
            filtered = self._filter_rows(reader, from_date, to_date)
            yield from chunked(filtered, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse Tidal's streaming.csv file into a listens batch"""
        listens = []
        for item in batch:
            artist_name = item["artist_name"]
            track_title = item["track_title"]

            listen: dict[str, Any] = {
                "listened_at": item["parsed_timestamp"],
                "track_metadata": {
                    "track_name": track_title,
                    "artist_name": artist_name
                },
            }

            additional_info: dict[str, Any] = {
                "submission_client": self.importer_name,
                "music_service": "tidal.com",
            }

            listen["track_metadata"]["additional_info"] = additional_info
            listens.append(listen)
        return listens

    @staticmethod
    def _looks_like_header(line: str) -> list[str] | None:
        maybe_header = [
            column.strip(' "').lower() for column in next(csv.reader([line]))
        ]
        expected = {"artist_name", "track_title", "entry_date"}
        if expected.issubset(maybe_header):
            return maybe_header
        return None

    @classmethod
    def _parse_datetime(cls, item: dict[str, Any]) -> datetime:
        time_zone = item.get("time_zone", "").strip()
        tzinfo = cls.DEFAULT_TIMEZONE
        if time_zone and time_zone.lower() != "null":
            try:
                tzinfo = ZoneInfo(time_zone)
            except ZoneInfoNotFoundError:
                current_app.logger.debug("Invalid Tidal timezone in item: %s", item, exc_info=True)

        return datetime.strptime(item["entry_date"], "%d/%m/%Y %H:%M").replace(tzinfo=tzinfo)

    def _filter_rows(
        self,
        reader: csv.DictReader,
        from_date: datetime,
        to_date: datetime,
    ) -> Iterator[dict[str, Any]]:
        for row in reader:
            try:
                date_time = self._parse_datetime(row)
            except (TypeError, ValueError):
                current_app.logger.debug("Invalid Timestamp in Tidal item: %s", row, exc_info=True)
                continue

            if not (from_date <= date_time <= to_date):
                continue

            yield {**row, "parsed_timestamp": int(date_time.timestamp())}

    def _read_header_line(self, file: TextIO) -> list[str]:
        file.seek(0)
        for line in file:
            header = self._looks_like_header(line)
            if header:
                return header
        raise ImportFailedError("Could not find Tidal header row in streaming file.")
