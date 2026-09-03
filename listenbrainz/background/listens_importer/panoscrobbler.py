import orjson
from flask import current_app
from datetime import datetime, timezone
from typing import Iterator, Any

from listenbrainz.background.listens_importer.base import BaseListensImporter


class PanoScrobblerListensImporter(BaseListensImporter):
    """PanoScrobbler-specific listens importer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "PanoScrobbler Archive Importer"

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the PanoScrobbler JSONL archive file and returns a generator of batches of items."""
        from_date = import_task["from_date"]
        to_date = import_task["to_date"]
        with open(import_task["file_path"], mode="rb") as file:
            batch = []
            for line in file:
                if not line.strip():
                    continue
                try:
                    item = orjson.loads(line)
                    if item is not None and item.get("timeMs") is not None:
                        timestamp = datetime.fromtimestamp(item.get("timeMs") / 1000.0, tz=timezone.utc)
                        if from_date <= timestamp <= to_date:
                            batch.append(item)
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []
                except (ValueError, KeyError, TypeError, OSError) as e:
                    current_app.logger.error(
                        f"Error parsing item: {item}. Error: {e}", exc_info=True)
                except orjson.JSONDecodeError:
                    current_app.logger.error(f"Skipping malformed JSON line: {line.strip().decode('utf-8', 'ignore')}")
            if batch:
                yield batch

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse items from PanoScrobbler export to a listens batch.
        """
        listens = []
        for item in batch:
            try:
                if not item.get("track"):
                    continue
                
                track_metadata = {
                    "track_name": item.get("track"),
                    "artist_name": item.get("artist"),
                }
                if item.get("album"):
                    track_metadata["release_name"] = item["album"]

                additional_info = {}
                if item.get("albumArtist"):
                    additional_info["album_artist_name"] = item["albumArtist"]
                if item.get("durationMs") is not None:
                    additional_info["duration_ms"] = item["durationMs"]

                if item.get("mediaPlayerName"):
                    additional_info["media_player"] = item.get("mediaPlayerName")
                if item.get("mediaPlayerVersion"):
                    additional_info["media_player_version"] = item.get("mediaPlayerVersion")
                
                additional_info["submission_client"] = self.importer_name

                timestamp = item["timeMs"] / 1000.0
                track_metadata["additional_info"] = additional_info
                listens.append({
                    "listened_at": timestamp,
                    "track_metadata": track_metadata,
                })
            except (ValueError, KeyError, TypeError) as e:
                current_app.logger.error(f"Error parsing item: {item}. Error: {e}", exc_info=True)  
                continue
        return listens
