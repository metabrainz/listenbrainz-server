# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import datetime


class Listen(object):
    """ Represents a listen object """
    def __init__(self, uid=None, timestamp=None, artist_msid=None, album_msid=None,
                 recording_msid=None, data=None):
        self.uid = uid
        self.timestamp = timestamp
        self.artist_msid = artist_msid
        self.album_msid = album_msid
        self.recording_msid = recording_msid
        self.data = {}

    @classmethod
    def from_json(cls, j):
        """Factory to make Listen() objects from a dict"""
        woo =  cls(  uid=j['user_id']
                   , timestamp=j['listened_at']
                   , artist_msid=j['track_metadata']['additional_info'].get('artist_msid')
                   , album_msid=j['track_metadata']['additional_info'].get('album_msid')
                   , recording_msid=j.get('recording_msid')
                   )
        # Uhm, if I pass data as the call above, the data vanishes. Setting it seperately is ok.
        woo.data = j['track_metadata']
        return woo

    def validate(self):
        return (self.uid is not None and self.timestamp is not None and self.artist_msid is not None
                and self.recording_msid is not None and self.data is not None)

    @property
    def date(self):
        return datetime.datetime.fromtimestamp(self.timestamp)

    def __repr__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        return u"<Listen: uid: %s, time: %s, artist_msid: %s, album_msid: %s, recording_msid: %s>" % \
               (self.uid, self.timestamp, self.artist_msid, self.album_msid, self.recording_msid)
