# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals


class Listen(object):
    """ Represents a listen object """
    def __init__(self, uid=None, timestamp=None, artist_msid=None, album_msid=None,
                 track_msid=None, data=None):
        self.uid = uid
        self.timestamp = timestamp
        self.artist_msid = artist_msid
        self.album_msid = album_msid
        self.track_msid = track_msid
        self.data = {}

    def validate(self):
        return (self.uid is not None and self.timestamp is not None and self.artist_msid is not None
                and self.track_msid is not None and self.data is not None)

    @property
    def date(self):
        return self.timestamp.date()

    def __repr__(self):
        return "<Listen: uid: %s, timestamp: %s, artist_msid: %s, album_msid: %s, track_msid: %s" % \
               (self.uid, self.timestamp, self.artist_msid, self.album_msid, self.track_msid)
