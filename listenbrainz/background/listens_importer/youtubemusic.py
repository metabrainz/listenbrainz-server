import json
import re
from datetime import datetime, timezone
from typing import Any, Iterator

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.metadata_cache.youtube.handler import YouTubeCacheHandler


class YouTubeMusicListensImporter(BaseListensImporter):
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
            if item.get("header") != "YouTube Music":
                continue

            try:
                time_str = item.get("time", "")
                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except (TypeError, ValueError):
                current_app.logger.error("Invalid YouTube timestamp in item: %s", item, exc_info=True)
                continue

            if from_date <= timestamp <= to_date:
                youtube_music_items.append(item)

        if not youtube_music_items:
            return iter(())

        return chunked(youtube_music_items, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert a batch of YouTube Music items into ListenBrainz listens.

        Items that already carry channel/subtitle information are converted
        directly. Items that only have a URL (no channel name) are collected
        and resolved via the YouTube metadata cache in a post-processing step.
        The cache checks its database first and only calls the YouTube Data
        API for entries that are not stored yet.
        """
        listens: list[dict[str, Any]] = []
        missing: list[tuple[dict[str, Any], str]] = []

        for item in batch:
            converted = self._convert_item_to_listen(item)
            if converted:
                listens.append(converted)
                continue

            # Only send entries for enrichment when  valid
            # and missing channel metadata.
            if not self._needs_metadata_enrichment(item):
                continue

            video_url = item.get("titleUrl", "")
            video_id = self._extract_video_id(video_url) if video_url else None
            if video_id:
                missing.append((item, video_id))

        if not missing:
            return listens

        # Deduplicate ids before the cache lookup so we issue as few API
        # calls as possible (the cache already batches up to 50 per request).
        unique_ids = list({vid for _, vid in missing})

        handler = YouTubeCacheHandler(current_app._get_current_object())
        video_meta = handler.lookup(unique_ids)

        for item, video_id in missing:
            meta = video_meta.get(video_id)
            if not meta:
                continue
            item["title"] = meta.title
            item["subtitles"] = [{"name": meta.channel_name}]
            converted = self._convert_item_to_listen(item)
            if converted:
                listens.append(converted)

        return listens

    def _convert_item_to_listen(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Attempt to convert a single history item into a ListenBrainz listen.

        Returns the listen dict on success or None if required metadata is
        missing (title or channel).
        """
        try:
            title = item.get("title", "")
            if title.startswith("Watched "):
                title = title[8:]

            if not title:
                return None

            subtitles = item.get("subtitles", [])
            channel_name = ""
            if subtitles and isinstance(subtitles, list):
                channel_name = subtitles[0].get("name", "")

            if not channel_name:
                return None

            if channel_name.endswith(" - Topic"):
                channel_name = channel_name[:-8]

            track_metadata: dict[str, Any] = {
                "artist_name": channel_name,
                "track_name": title,
            }

            additional_info: dict[str, Any] = {
                "submission_client": self.importer_name,
                "music_service": "music.youtube.com",
            }

            video_url = item.get("titleUrl", "")
            if video_url:
                additional_info["origin_url"] = video_url
                vid = self._extract_video_id(video_url)
                if vid:
                    additional_info["youtube_id"] = vid

            track_metadata["additional_info"] = additional_info

            time_str = item.get("time", "")
            timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            listened_at = int(timestamp.timestamp())

            return {"listened_at": listened_at, "track_metadata": track_metadata}

        except (KeyError, TypeError, ValueError):
            current_app.logger.error("Error parsing YouTube item: %s", item, exc_info=True)
            return None

    def _needs_metadata_enrichment(self, item: dict[str, Any]) -> bool:
        """Return True when an item is valid except for missing channel info."""
        title = item.get("title", "")
        if title.startswith("Watched "):
            title = title[8:]
        if not title:
            return False

        # Batch filtering already validates timestamp, but keeping this as a guard
        # so we don't enrich malformed entries if this method is reused later.
        time_str = item.get("time", "")
        try:
            datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except (TypeError, ValueError):
            return False

        subtitles = item.get("subtitles", [])
        if subtitles and isinstance(subtitles, list):
            channel_name = subtitles[0].get("name", "")
            if channel_name:
                return False

        return True

    def _extract_video_id(self, video_url: str) -> str | None:
        patterns = [
            r"watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"embed/([^?]+)",
            r"v/([^?]+)",
            r"e/([^?]+)",
        ]

        for pat in patterns:
            m = re.search(pat, video_url)
            if m:
                return m.group(1)

        return None
