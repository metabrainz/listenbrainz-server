import json
import re
from datetime import datetime, timezone
from typing import Any, Iterator

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter


class YouTubeListensImporter(BaseListensImporter):
    """Importer for YouTube Music listening history exports."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "YouTube Music History Importer"

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Read the YouTube JSON export and yield filtered YouTube Music items in batches."""
        from_date = import_task["from_date"]
        to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="r", encoding="utf-8") as infile:
            data = json.load(infile)

        youtube_music_items: list[dict[str, Any]] = []
        for item in data:
            # Only process YouTube Music items
            if item.get("header") != "YouTube Music":
                continue

            try:
                time_str = item.get("time", "")
                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except (KeyError, TypeError, ValueError):
                current_app.logger.error("Invalid YouTube timestamp in item: %s", item, exc_info=True)
                continue

            if from_date <= timestamp <= to_date:
                youtube_music_items.append(item)

        if not youtube_music_items:
            return iter(())

        return chunked(youtube_music_items, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert YouTube Music items into ListenBrainz listen payloads."""
        listens: list[dict[str, Any]] = []

        for item in batch:
            try:
                title = item.get("title", "")
                if title.startswith("Watched "):
                    title = title[8:]

                if not title:
                    continue

                channel_name = ""
                subtitles = item.get("subtitles", [])
                if subtitles and isinstance(subtitles, list):
                    channel_name = subtitles[0].get("name", "")

                track_name = title
                artist_name = channel_name if channel_name else "Unknown Artist"

                track_metadata: dict[str, Any] = {
                    "artist_name": artist_name,
                    "track_name": track_name,
                }

                additional_info: dict[str, Any] = {
                    "submission_client": self.importer_name,
                    "music_service": "youtube.com",
                }

                video_url = item.get("titleUrl", "")
                if video_url:
                    additional_info["origin_url"] = video_url
                    video_id = self._extract_video_id(video_url)
                    if video_id:
                        additional_info["youtube_id"] = video_id

                track_metadata["additional_info"] = additional_info
                time_str = item.get("time", "")
                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                listened_at = int(timestamp.timestamp())

                listens.append({
                    "listened_at": listened_at,
                    "track_metadata": track_metadata,
                })

            except (KeyError, TypeError, ValueError):
                current_app.logger.error("Error parsing YouTube item: %s", item, exc_info=True)
                continue

        return listens

    def _extract_video_id(self, url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'watch\?v=([^&]+)',
            r'youtu\.be/([^?]+)',
            r'embed/([^?]+)',
            r'v/([^?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None