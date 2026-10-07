import re
from datetime import datetime
from typing import Any, Iterator, TypedDict
from urllib.parse import parse_qs, urlparse

import ijson
from flask import current_app

from listenbrainz.background.listens_importer.base import BaseListensImporter
from listenbrainz.metadata_cache.youtube.handler import YouTubeCacheHandler


class YouTubeSubtitle(TypedDict, total=False):
    name: str
    url: str


class YouTubeHistoryItem(TypedDict, total=False):
    header: str
    title: str
    titleUrl: str
    subtitles: list[YouTubeSubtitle]
    time: str


class YouTubeMusicListensImporter(BaseListensImporter):
    """Importer for YouTube Music listening history exports."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer_name = "YouTube Music History Importer"

    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Read the YouTube JSON export and yield filtered YouTube Music items in batches."""
        from_date = import_task["from_date"]
        to_date = import_task["to_date"]

        with open(import_task["file_path"], mode="rb") as infile:
            batch: list[dict[str, Any]] = []
            for item in ijson.items(infile, "item"):
                if item.get("header") != "YouTube Music":
                    continue

                try:
                    time_str = item.get("time", "")
                    timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except (TypeError, ValueError):
                    current_app.logger.error("Invalid YouTube timestamp in item: %s", item, exc_info=True)
                    continue

                if from_date <= timestamp <= to_date:
                    batch.append(item)
                    if len(batch) >= self.batch_size:
                        yield batch
                        batch = []

            if batch:
                yield batch

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert a batch of YouTube Music items into ListenBrainz listens.

        Items with usable titles and channel information are converted directly.
        Items with missing metadata or URL-placeholder titles are collected
        and resolved via the YouTube metadata cache in a post-processing step.
        The cache checks its database first and only calls the YouTube Data
        API for entries that are not stored yet.
        """
        listens: list[dict[str, Any]] = []
        missing: list[tuple[dict[str, Any], str]] = []

        for item in batch:
            # Only send entries for enrichment when they have invalid or missing metadata
            if not self._needs_metadata_enrichment(item):
                converted = self._convert_item_to_listen(item, from_takeout=True)
                if converted:
                    listens.append(converted)
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
            enriched_item = {
                **item,
                "title": meta.title,
                "subtitles": [{"name": meta.channel_name}],
            }
            converted = self._convert_item_to_listen(enriched_item, from_takeout=False)
            if converted:
                if meta.duration_ms is not None:
                    converted["track_metadata"]["additional_info"]["duration_ms"] = meta.duration_ms
                listens.append(converted)

        return listens

    def _convert_item_to_listen(self, item: YouTubeHistoryItem, *, from_takeout: bool = True) -> dict[str, Any] | None:
        """Attempt to convert a single history item into a ListenBrainz listen.

        Returns the listen dict on success or None if required metadata is
        missing (title or channel). Only Takeout titles contain an activity prefix;
        titles recovered from the API must be preserved as returned.
        """
        try:
            title = item.get("title", "")
            if not isinstance(title, str):
                return None
            if from_takeout and title.startswith("Watched "):
                title = title.removeprefix("Watched ")

            if not title:
                return None

            subtitles = item.get("subtitles", [])
            channel_name = ""
            if subtitles and isinstance(subtitles, list):
                channel_name = subtitles[0].get("name", "")

            if not channel_name:
                return None

            if channel_name.endswith(" - Topic"):
                channel_name = channel_name.removesuffix(" - Topic")

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
        """Return True when the title or channel metadata is missing or unusable."""
        title = item.get("title", "")
        if not isinstance(title, str):
            return True

        title = title.removeprefix("Watched ").strip()
        if not title or title.lower().startswith(("https://", "http://")):
            return True

        subtitles = item.get("subtitles", [])
        if not subtitles:
            return True
        if subtitles and isinstance(subtitles, list):
            channel_name = subtitles[0].get("name", "")
            if not isinstance(channel_name, str) or not channel_name.strip():
                return True

        return False

    @staticmethod
    def _extract_video_id(video_url: str) -> str | None:
        parsed_url = urlparse(video_url)
        hostname = (parsed_url.hostname or "").removeprefix("www.")
        video_id = None

        if hostname == "youtu.be":
            video_id = parsed_url.path.lstrip("/").split("/", 1)[0]
        elif hostname.endswith("youtube.com"):
            if parsed_url.path == "/watch":
                video_id = parse_qs(parsed_url.query).get("v", [None])[0]
            else:
                path_parts = parsed_url.path.strip("/").split("/")
                if len(path_parts) == 2 and path_parts[0] in {"embed", "v", "e", "shorts"}:
                    video_id = path_parts[1]

        if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id
        return None
