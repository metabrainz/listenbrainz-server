import csv
from datetime import datetime, timezone
from typing import Any, Iterator, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.db import user_setting as db_usersetting


class AudioscrobblerListensImporter(BaseListensImporter):
    DEFAULT_FIELDNAMES = [
        "artist_name",
        "release_name",
        "track_name",
        "tracknumber",
        "duration",
        "rating",
        "timestamp",
        "track_mbid",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "Audioscrobbler Archive Importer"
        self.original_client = None
        self.timezone = None

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Process Audioscrobbler .scrobbler.log files.

        Lines starting with `#` are treated as comments and ignored, except
        for `#CLIENT/` which is stored as original submission client and `#TZ/` which
        indicates the timezone. Field order is fixed as defined in DEFAULT_FIELDNAMES;
        header aliases are ignored.
        """

        from_date = import_task["from_date"]
        to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8", errors="replace") as file:
            self._parse_header(file)
            
            if self.timezone is None:
                user_timezone_override = import_task.get("metadata", {}).get("user_timezone")
                if user_timezone_override:
                    timezone_name = user_timezone_override
                else:
                    user_settings = db_usersetting.get(self.db_conn, import_task["user_id"])
                    timezone_name = user_settings.get("timezone_name", "UTC")
                
                try:
                    self.timezone = ZoneInfo(timezone_name)
                except ZoneInfoNotFoundError:
                    current_app.logger.warning(f"Unknown timezone '{timezone_name}' for user {import_task['user_id']}, defaulting to UTC.")
                    self.timezone = ZoneInfo("UTC")

            file.seek(0) # Reset to beginning after extracting header metadata

            reader = csv.DictReader(
                (line for line in file if line.strip() and not line.strip().startswith("#")),
                fieldnames=self.DEFAULT_FIELDNAMES,
                delimiter="\t"
            )
            filtered = self._filtered_rows(reader, from_date, to_date)
            yield from chunked(filtered, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        listens = []
        for item in batch:
            listen = {
                "listened_at": int(item["timestamp"]),
                "track_metadata": {
                    "artist_name": item["artist_name"],
                    "track_name": item["track_name"],
                    "additional_info": {
                        "submission_client": self.importer_name,
                    },
                },
            }

            track_metadata = listen["track_metadata"]
            additional_info = track_metadata["additional_info"]

            if self.original_client:
                additional_info["original_submission_client"] = self.original_client

            if item.get("release_name"):
                track_metadata["release_name"] = item["release_name"]

            if item.get("duration"):
                try:
                    additional_info["duration"] = int(item["duration"])
                except (TypeError, ValueError):
                    current_app.logger.debug("Skipping invalid duration in Audioscrobbler row: %s", item)

            if item.get("tracknumber"):
                additional_info["tracknumber"] = item["tracknumber"]

            if item.get("track_mbid"):
                additional_info["track_mbid"] = item["track_mbid"]

            listens.append(listen)

        return listens

    def _parse_header(self, file: TextIO) -> None:
        """Extract metadata from header comment lines."""
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("#"):
                if stripped.startswith("#CLIENT/"):
                    self.original_client = stripped.removeprefix("#CLIENT/").strip().replace("$Revision$", "").strip()
                elif stripped.startswith("#TZ/"):
                    tz_value = stripped.removeprefix("#TZ/").strip()
                    self.timezone = ZoneInfo("UTC") if tz_value == "UTC" else None
            else:
                break

    def _filtered_rows(self, reader: csv.DictReader, from_date: datetime, to_date: datetime) -> Iterator[dict[str, Any]]:
        for row in reader:
            if None in row:
                current_app.logger.debug("Skipping malformed Audioscrobbler row with extra fields: %s", row)
                continue

            if not row.get("artist_name") or not row.get("track_name") or not row.get("timestamp"):
                current_app.logger.debug("Skipping Audioscrobbler row with missing required fields: %s", row)
                continue

            artist_name = row.get("artist_name", "")
            if artist_name == "<Untagged>":
                current_app.logger.debug("Skipping Audioscrobbler row with untagged artist: %s", row)
                continue

            rating = row.get("rating")
            if rating != "L":
                continue # 'L' if listened at least 50% or 'S' if skipped

            try:
                ts = int(row["timestamp"])
            except (TypeError, ValueError):
                current_app.logger.debug("Skipping Audioscrobbler row with invalid timestamp: %s", row)
                continue

            try:
                listened_at = datetime.fromtimestamp(ts, tz=timezone.utc)

                if self.timezone and str(self.timezone) != "UTC":
                    # Adjust timestamps from user's local timezone to UTC
                    raw_ts = datetime.utcfromtimestamp(ts)
                    adjusted_ts = raw_ts.replace(tzinfo=self.timezone)
                    listened_at = adjusted_ts.astimezone(timezone.utc)
                    ts = int(listened_at.timestamp())
            except (ValueError, OSError) as e:
                current_app.logger.error("Error converting timestamp in Audioscrobbler row: %s, error: %s", row, e)
                continue

            if not (from_date <= listened_at <= to_date):
                current_app.logger.debug("Skipping Audioscrobbler listen outside date range: %s", row)
                continue

            row["timestamp"] = ts
            yield row
