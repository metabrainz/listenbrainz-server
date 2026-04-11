import logging

import requests
from datetime import datetime, timezone
from more_itertools import chunked
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.unique_queue import JobItem
from listenbrainz.metadata_cache.youtube.models import YouTubeVideo

logger = logging.getLogger(__name__)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeCacheHandler(BaseHandler):

    def __init__(self, app):
        super().__init__(
            name="listenbrainz-youtube-metadata-cache",
            external_service_queue=""
        )
        self.app = app

    def get_items_from_listen(self, listen) -> list[JobItem]:
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        return []

    def get_seed_ids(self) -> list[str]:
        return []

    def process(self, item_ids: list[str]) -> list[JobItem]:
        return []

    def lookup(self, video_ids: list[str]) -> dict[str, YouTubeVideo]:
        #Return cached metadata for the given video ids.

        if not video_ids:
            return {}

        cached = self._fetch_from_db(video_ids)

        missing = [vid for vid in video_ids if vid not in cached]
        if not missing:
            return cached

        api_key = self.app.config.get("YOUTUBE_API_KEY")
        if not api_key:
            logger.warning("YOUTUBE_API_KEY not set; skipping API lookup for %d ids", len(missing))
            return cached

        fetched = self._fetch_from_api(missing, api_key)
        if fetched:
            self._upsert(fetched)
            cached.update({v.video_id: v for v in fetched})

        return cached

    def _fetch_from_db(self, video_ids: list[str]) -> dict[str, YouTubeVideo]:
        """Return a dict of video_id -> YouTubeVideo for ids already cached."""
        with timescale.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT video_id, title, channel_name
                      FROM youtube_cache.video
                     WHERE video_id = ANY(:video_ids)
                """),
                {"video_ids": video_ids},
            )
            rows = result.fetchall()

        return {
            row[0]: YouTubeVideo(video_id=row[0], title=row[1], channel_name=row[2])
            for row in rows
        }

    def _fetch_from_api(self, video_ids: list[str], api_key: str) -> list[YouTubeVideo]:
        #Fetch video snippet data from the YouTube Data API
        
        results = []
        for id_chunk in chunked(video_ids, 50):
            params = {
                "part": "snippet",
                "id": ",".join(id_chunk),
                "key": api_key,
            }
            try:
                resp = requests.get(YOUTUBE_API_URL, params=params, timeout=10)
                resp.raise_for_status()
            except Exception:
                logger.exception("YouTube API request failed for ids: %s", id_chunk)
                continue

            for item in resp.json().get("items", []):
                video_id = item.get("id")
                snippet = item.get("snippet", {})
                title = snippet.get("title", "")
                channel_name = snippet.get("channelTitle", "")
                if video_id and title and channel_name:
                    results.append(YouTubeVideo(video_id=video_id, title=title, channel_name=channel_name))

        return results

    def _upsert(self, videos: list[YouTubeVideo]):
        """Bulk-insert (or update) a list of YouTubeVideo entries in the cache table."""
        query = """
            INSERT INTO youtube_cache.video (video_id, title, channel_name, last_updated)
                 VALUES %s
            ON CONFLICT (video_id)
              DO UPDATE
                    SET title = EXCLUDED.title
                      , channel_name = EXCLUDED.channel_name
                      , last_updated = EXCLUDED.last_updated
        """
        values = [(v.video_id, v.title, v.channel_name, datetime.now(timezone.utc)) for v in videos]

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(curs, query, values)
            conn.commit()
        finally:
            conn.close()
