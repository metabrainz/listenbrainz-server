from datasethoster import Query

from listenbrainz.labs_api.labs.api.spotify.utils import lookup_using_metadata


class SpotifyIdFromMetadataQuery(Query):
    """ Query to lookup spotify track ids using artist name, release name and track name. """

    def names(self):
        return "spotify-id-from-metadata", "Spotify Track ID Lookup using metadata"

    def inputs(self):
        return ['[artist_name]', '[release_name]', '[track_name]']

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in Spotify."""

    def outputs(self):
        return ['artist_name', 'release_name', 'track_name', 'spotify_track_ids']

    def fetch(self, params, offset=-1, count=-1):
        data = []
        for param in params:
            data.append({
                "artist_name": param.get("[artist_name]", ""),
                "release_name": param.get("[release_name]", ""),
                "track_name": param.get("[track_name]", "")
            })
        return lookup_using_metadata(data)
