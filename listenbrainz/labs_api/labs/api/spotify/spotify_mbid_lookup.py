from flask import current_app

from listenbrainz.labs_api.labs.api.metadata_index.metadata_index_from_mbid_lookup import MetadataIndexFromMBIDQuery
from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput
from listenbrainz.labs_api.labs.api.utils import lookup_spotify_track_ids_from_mb_url_rels


class SpotifyIdFromMBIDQuery(MetadataIndexFromMBIDQuery):
    """ Query to lookup spotify track ids using recording mbids. """

    def __init__(self):
        super().__init__("spotify")

    def names(self):
        return "spotify-id-from-mbid", "Spotify Track ID Lookup using recording mbid"

    def introduction(self):
        return """Given a recording mbid, lookup its metadata using canonical metadata
        tables and using that attempt to find a suitable match in Spotify. Recordings
        that are not matched by the metadata index fall back to MusicBrainz URL
        relationships, which map recording MBIDs directly to curated Spotify track URLs."""

    def outputs(self):
        return SpotifyIdFromMBIDOutput

    def fetch(self, params, source, offset=-1, count=-1):
        results = super().fetch(params, source, offset, count)

        # Fall back to MusicBrainz URL relationships for any recordings the metadata
        # index did not resolve. This catches cases where the normalized text lookup
        # fails (remaster suffixes, non-Latin scripts, featured-artist drift, etc.)
        # and also cases where the input MBID is not present in the canonical
        # metadata tables at all (in which case the base class drops it silently).
        input_mbids = [str(p.recording_mbid) for p in params]
        resolved_mbids = {str(r.recording_mbid) for r in results if r.spotify_track_ids}
        unresolved = [m for m in input_mbids if m not in resolved_mbids]

        if unresolved:
            try:
                url_rel_matches = lookup_spotify_track_ids_from_mb_url_rels(unresolved)
            except Exception:
                current_app.logger.error("URL relationship fallback failed, returning metadata index results only",
                                         exc_info=True)
                return results

            # Update existing result rows (empty spotify_track_ids) where we now have a match
            result_by_mbid = {str(r.recording_mbid): r for r in results}
            for mbid, track_ids in url_rel_matches.items():
                if mbid in result_by_mbid:
                    result_by_mbid[mbid].spotify_track_ids = track_ids
                else:
                    # MBID was dropped by the base class (not in canonical metadata); construct a new row
                    results.append(self.outputs()(
                        recording_mbid=mbid,
                        artist_name=None,
                        release_name=None,
                        track_name=None,
                        spotify_track_ids=track_ids,
                    ))

        return results
