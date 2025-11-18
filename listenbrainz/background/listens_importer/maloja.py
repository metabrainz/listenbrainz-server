import json
from datetime import datetime, timezone
from typing import Any, Iterator
import pdb

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter


class MalojaListensImporter(BaseListensImporter):
    """Importer for Maloja listening history exports."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "Maloja Archive Importer"

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Read the Maloja JSON export and yield filtered scrobbles in batches."""
        from_date = import_task["from_date"]
        to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", encoding="utf-8") as infile:
            data = json.load(infile)

        scrobbles = data.get("scrobbles", [])
        filtered_scrobbles: list[dict[str, Any]] = []
        for item in scrobbles:
            try:
                timestamp = datetime.fromtimestamp(item["time"], tz=timezone.utc)
            except (KeyError, TypeError, ValueError, OSError):
                current_app.logger.error("Invalid Maloja timestamp in item: %s", item, exc_info=True)
                continue

            if from_date <= timestamp <= to_date:
                filtered_scrobbles.append(item)

        if not filtered_scrobbles:
            return iter(())

        return chunked(filtered_scrobbles, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Maloja scrobbles into ListenBrainz listen payloads."""
        listens: list[dict[str, Any]] = []

        for item in batch:
            pdb.set_trace()
            try:
                track = item.get("track", {}) or {}
                artists = track.get("artists", []) or []
                if not artists:
                    continue

                track_name = track.get("title")
                if not track_name:
                    continue

                artist_name = ", ".join(artists)
                track_metadata: dict[str, Any] = {
                    "artist_name": artist_name,
                    "track_name": track_name,
                }

                album = track.get("album") or {}
                album_title = album.get("albumtitle")
                if album_title:
                    track_metadata["release_name"] = album_title

                additional_info: dict[str, Any] = {
                    "submission_client": self.importer_name,
                }

                album_artists = album.get("artists", []) or []
                if album_artists and album_artists != artists:
                    additional_info["release_artist_name"] = ", ".join(album_artists)

                # duration_played = item.get("duration")
                # if duration_played:
                #     try:
                #         additional_info["duration_played"] = int(duration_played)
                #     except (TypeError, ValueError):
                #         current_app.logger.debug("Skipping invalid duration_played in Maloja item: %s", item, exc_info=True)

                duration_seconds = track.get("length")
                if duration_seconds:
                    try:
                        additional_info["duration"] = int(duration_seconds)
                    except (TypeError, ValueError):
                        current_app.logger.debug("Skipping invalid duration in Maloja item: %s", item, exc_info=True)

                origin = item.get("origin")
                if origin:
                    parsed_submission_client = self._parse_submission_client(origin)
                    if parsed_submission_client:
                        additional_info["original_submission_client"] = parsed_submission_client

                track_metadata["additional_info"] = additional_info

                listens.append({
                    "listened_at": int(item["time"]),
                    "track_metadata": track_metadata,
                })

            except (KeyError, TypeError, ValueError):
                current_app.logger.error("Error parsing Maloja scrobble: %s", item, exc_info=True)
                continue

        return listens

    @staticmethod
    def _parse_submission_client(origin: str) -> str | None:
        """Return the last colon-delimited token, keeping legacy/unknown intact."""
        cleaned = (origin or "").strip()
        if not cleaned:
            return None

        if cleaned in {"legacy", "unknown"}:
            return cleaned

        client = cleaned.split(":")[-1].strip()
        return client or None