import os
from datetime import datetime, timezone
from typing import Any, Iterator

import ijson
from flask import current_app
from spotipy import Spotify, SpotifyClientCredentials, SpotifyOauthError
from sqlalchemy import text

from listenbrainz.background.listens_importer.base import BaseListensImporter


class SpotifyListensImporter(BaseListensImporter):
    """Spotify-specific listens importer."""

    def _filter_zip_files(self, file: str) -> bool:
        filename = os.path.basename(file).lower()
        return filename.endswith(".json") and ("audio" in filename or "endsong" in filename)

    def _process_file_contents(self, contents: str) -> Iterator[tuple[datetime, Any]]:
        for entry in ijson.items(contents, "item"):
            timestamp = datetime.strptime(
                entry["ts"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            entry["timestamp"] = timestamp
            yield timestamp, entry

    def _parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse Spotify listen batch."""
        items = []
        for item in batch:
            try:
                if item["skipped"] or item["incognito_mode"]:
                    continue
                if item["ms_played"] < 30000:
                    if item["reason_end"] in ["fwdbtn", "clickrow", "playbtn", "remote"]:
                        continue
                items.append({
                    "artist_name": item.get("master_metadata_album_artist_name"),
                    "track_name": item.get("master_metadata_track_name"),
                    "timestamp": int(item["timestamp"].timestamp()),
                    "spotify_track_id": item["spotify_track_uri"].split(":")[2],
                    "ms_played": item.get("ms_played"),
                    "release_name": item.get("master_metadata_album_name", ""),
                })
            except:
                continue

        if not items:
            return []

        spotify_track_ids = {x["spotify_track_id"] for x in items}
        tracks = self._get_spotify_data(spotify_track_ids)

        listens = []
        for item in items:
            sp_track = tracks.get(item["spotify_track_id"])
            if sp_track:
                track_metadata = {
                    "artist_name": sp_track["artist_name"],
                    "track_name": sp_track["track_name"],
                    "release_name": sp_track["album_name"],
                }
                additional_info = {
                    "tracknumber": sp_track["track_number"],
                    "duration_ms": sp_track["duration_ms"],
                    "spotify_artist_ids": [
                        f"https://open.spotify.com/artist/{artist_id}" for artist_id in sp_track["artist_ids"]
                    ],
                    "spotify_album_id": f"https://open.spotify.com/album/{sp_track['album_id']}",
                    "spotify_album_artist_ids": [
                        f"https://open.spotify.com/artist/{artist_id}" for artist_id in sp_track["album_artist_ids"]
                    ],
                    "release_artist_name": sp_track["album_artist_name"],
                }
            elif item["artist_name"] and item["track_name"]:
                track_metadata = {
                    "artist_name": item["artist_name"],
                    "track_name": item["track_name"],
                }
                if item["release_name"]:
                    track_metadata["release_name"] = item["release_name"]
                additional_info = {}
            else:
                continue

            additional_info.update({
                "ms_played": item["ms_played"],
                "origin_url": f"https://open.spotify.com/track/{item['spotify_track_id']}",
                "submission_client": self.importer_name,
                "music_service": "spotify.com"
            })
            track_metadata["additional_info"] = additional_info
            listens.append({
                "listened_at": item["timestamp"],
                "track_metadata": track_metadata,
            })
        return listens

    def _get_spotify_data(self, spotify_track_ids: set[str]) -> dict[str, dict[str, Any]]:
        """Get Spotify data from cache and API."""
        tracks = self._get_spotify_data_from_cache(list(spotify_track_ids))
        remaining_track_ids = spotify_track_ids - set(tracks.keys())
        if remaining_track_ids:
            try:
                api_tracks = self._get_spotify_data_from_api(list(remaining_track_ids))
                tracks.update(api_tracks)
            except SpotifyOauthError:
                current_app.logger.error("Spotify OAuth error, skipping API call data fetch", exc_info=True)
        return tracks

    def _get_spotify_data_from_cache(self, spotify_track_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Get Spotify track data from cache for multiple track IDs."""
        if not spotify_track_ids:
            return {}

        query = """\
            SELECT t.track_id AS track_id
                 , t.name AS track_name
                 , t.track_number
                 , t.data->'duration_ms' AS duration_ms
                 , al.album_id AS album_id
                 , al.name AS album_name
                 , aal.artist_name AS album_artist_name
                 , aal.artist_ids AS album_artist_ids
                 , tal.artist_name AS artist_name
                 , tal.artist_ids AS artist_ids
             FROM spotify_cache.track t
             JOIN spotify_cache.album al
               ON t.album_id = al.album_id
        LEFT JOIN LATERAL (
                    SELECT array_agg(aa.artist_id ORDER BY raa.position) AS artist_ids
                         , string_agg(aa.name, ', 'ORDER BY raa.position) AS artist_name
                      FROM spotify_cache.rel_album_artist raa
                      JOIN spotify_cache.artist aa
                        ON raa.artist_id = aa.artist_id
                     WHERE raa.album_id = al.album_id
                  ) aal
               ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(ta.artist_id ORDER BY rta.position) AS artist_ids
                         , string_agg(ta.name, ', 'ORDER BY rta.position) AS artist_name
                      FROM spotify_cache.rel_track_artist rta
                      JOIN spotify_cache.artist ta
                        ON rta.artist_id = ta.artist_id
                     WHERE rta.track_id = t.track_id
                  ) tal
               ON TRUE
            WHERE t.track_id = '50DMJJpAeQv4fIpxZvQz2e';
        """
        result = self.ts_conn.execute(text(query), {"track_ids": spotify_track_ids})
        return {r.track_id: dict(r) for r in result.mappings()}

    def _get_spotify_data_from_api(self, spotify_track_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Get Spotify track data from the API for multiple track IDs."""
        if not spotify_track_ids:
            return {}

        sp = Spotify(auth_manager=SpotifyClientCredentials(
            client_id=current_app.config["SPOTIFY_CLIENT_ID"],
            client_secret=current_app.config["SPOTIFY_CLIENT_SECRET"]
        ))

        results = {}
        for i in range(0, len(spotify_track_ids), 50):
            batch = spotify_track_ids[i: i + 50]
            try:
                tracks = sp.tracks(batch)
                for track in tracks.get("tracks", []):
                    if not track:
                        continue

                    track_id = track["id"]

                    artist_ids, artist_names = [], []
                    for artist in track["artists"]:
                        artist_ids.append(artist["id"])
                        artist_names.append(artist["name"])

                    album = track["album"]
                    album_artists = album.get("artists")
                    album_artist_ids, album_artist_names = [], []
                    for artist in album_artists:
                        album_artist_ids.append(artist["id"])
                        album_artist_names.append(artist["name"])

                    results[track_id] = {
                        "track_id": track_id,
                        "track_name": track["name"],
                        "track_number": track.get("track_number"),
                        "duration_ms": track.get("duration_ms"),
                        "album_id": album["id"],
                        "album_name": album["name"],
                        "album_artist_name": ", ".join(album_artist_names),
                        "album_artist_ids": album_artist_ids,
                        "artist_name": ", ".join(artist_names),
                        "artist_ids": artist_ids,
                    }
            except Exception as e:
                current_app.logger.error(f"Error fetching Spotify tracks {batch}: {str(e)}", exc_info=True)

        return results
