from troi import Recording, Artist, ArtistCredit
from troi.plist import plist
from troi.service import Service

from listenbrainz.db.lb_radio_artist import lb_radio_artist


class RecordingSearchByArtistService(Service):
    """Replaces troi.recording_search_service.RecordingSearchByArtistService.

    Calls lb_radio_artist() directly instead of the HTTP loopback to
    /1/lb-radio/artist/<mbid>. Object construction and random_item call are
    copied verbatim from the troi original so return shape is identical.
    """

    SLUG = "recording-search-by-artist"

    def __init__(self):
        super().__init__(self.SLUG)

    def search(self, mode, artist_mbid, pop_begin, pop_end, max_recordings_per_artist, max_similar_artists):
        artists = lb_radio_artist(
            mode,
            artist_mbid,
            max_similar_artists,
            max_recordings_per_artist,
            pop_begin / 100.0,
            pop_end / 100.0,
        )

        artist_recordings = {}
        msgs = []
        for artist_mbid in artists:
            recordings = plist()
            for recording in artists[artist_mbid]:
                artist_credit = ArtistCredit(artists=[Artist(mbid=recording["similar_artist_mbid"])],
                                             name=recording["similar_artist_name"])
                recordings.append(Recording(mbid=recording["recording_mbid"],
                                            artist_credit=artist_credit,
                                            musicbrainz={"total_listen_count": recording["total_listen_count"]}))

            # Below is a hack, since the endpoint seems to return one track too few
            if 0 < len(recordings) < max_recordings_per_artist - 1:
                msgs.append("Artist %s has only few top recordings in %s mode" % (recordings[0].artist_credit.name, mode))

            artist_recordings[artist_mbid] = recordings.random_item(pop_begin, pop_end, max_recordings_per_artist)

        return artist_recordings, msgs
