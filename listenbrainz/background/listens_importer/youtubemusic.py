import json
import re
import requests
from datetime import datetime
from typing import Any, Iterator, TypedDict
from urllib.parse import parse_qs, urlparse

from flask import current_app
from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter


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

        with open(import_task["file_path"], mode="r", encoding="utf-8") as infile:
            data = json.load(infile)

        youtube_music_items: list[YouTubeHistoryItem] = []
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

        This method performs a best-effort conversion of items that include
        channel/subtitle information. Entries that only contain a URL are
        collected for a post-processing step (outside this loop) where we can
        batch-request the YouTube Data API to fill missing metadata.
        """
        listens: list[dict[str, Any]] = []
        missing: list[tuple[dict[str, Any], str | None]] = []

        for item in batch:
            converted = self._convert_item_to_listen(item)
            if converted:
                listens.append(converted)
                continue
            video_url = item.get("titleUrl", "")
            video_id = self._extract_video_id(video_url) if video_url else None
            missing.append((item, video_id))

        api_key = current_app.config.get("YOUTUBE_API_KEY")
        if missing and api_key:
            id_map: dict[str, list[YouTubeHistoryItem]] = {}
            for orig, vid in missing:
                if not vid:
                    continue
                id_map.setdefault(vid, []).append(orig)

            if id_map:
                for ids_chunk in chunked(id_map.keys(), 50):
                    try:
                        metas = self._fetch_videos_metadata(ids_chunk)
                    except Exception:
                        current_app.logger.exception("YouTube API batch fetch failed")
                        continue
                    for vid in ids_chunk:
                        item_meta = metas.get(vid)
                        if not item_meta:
                            continue
                        snippet = item_meta.get("snippet", {})
                        for orig in id_map.get(vid, []):
                            title = snippet.get("title")
                            channel_name = snippet.get("channelTitle")
                            if not title or not channel_name:
                                continue
                            enriched_item = {
                                **orig,
                                "title": title,
                                "subtitles": [{"name": channel_name}],
                            }
                            converted_listen = self._convert_item_to_listen(enriched_item)
                            if converted_listen:
                                listens.append(converted_listen)

        return listens

    def _convert_item_to_listen(self, item: YouTubeHistoryItem) -> dict[str, Any] | None:
        """Attempt to convert a single history item into a ListenBrainz listen.

        Returns the listen dict on success or None if required metadata is
        missing (title or channel).
        """
        try:
            title = item.get("title", "")
            if title.startswith("Watched "):
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

        except (TypeError, ValueError):
            current_app.logger.error("Error parsing YouTube item: %s", item, exc_info=True)
            return None

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

    def _fetch_videos_metadata(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch metadata for up to 50 YouTube video IDs via the Data API.

        Returns a dict mapping video_id -> metadata (the API item object).
        """
        api_key = current_app.config.get("YOUTUBE_API_KEY")
        if not api_key:
            raise RuntimeError("YOUTUBE_API_KEY not configured")

        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "id": ",".join(video_ids),
            "key": api_key,
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        return {item["id"]: item for item in items if item.get("id") is not None}
