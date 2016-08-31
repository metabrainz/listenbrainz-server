# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ujson
from datetime import datetime
import calendar

class Listen(object):
    """ Represents a listen object """
    def __init__(self, user_id=None, user_name=None, timestamp=None, artist_msid=None, album_msid=None,
                 recording_msid=None, artist_name=None, track_name=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        # determine the type of timestamp and do the right thing
        if isinstance(timestamp, int) or isinstance(timestamp, float):
            self.ts_since_epoch = int(timestamp)
            self.timestamp = datetime.utcfromtimestamp(self.ts_since_epoch)
        else:
            self.timestamp = timestamp
            self.ts_since_epoch = calendar.timegm(self.timestamp.utctimetuple())

        self.artist_msid = artist_msid
        self.album_msid = album_msid
        self.recording_msid = recording_msid
        if data is None:
            self.data = {'additional_info': {}}
        else:
            self.data = data

        self.data['artist_name'] = artist_name
        self.data['track_name'] = track_name

    @classmethod
    def from_json(cls, j):
        """Factory to make Listen() objects from a dict"""
        return cls(user_id=j['user_id'], 
            user_name=j.get('user_name', ""),
            timestamp=datetime.utcfromtimestamp(float(j['listened_at'])),
            artist_msid=j['track_metadata']['additional_info'].get('artist_msid'),
            album_msid=j['track_metadata']['additional_info'].get('album_msid'),
            recording_msid=j.get('recording_msid'),
            data=j.get('track_metadata')
        )

    def to_json(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'timestamp': self.timestamp,
            'track_metadata': self.data,
            'recording_msid': self.recording_msid
        }

    def validate(self):
        return (self.user_id is not None and self.timestamp is not None and self.artist_msid is not None
                and self.recording_msid is not None and self.data is not None)

    @property
    def date(self):
        return self.timestamp

    def __repr__(self):
        return unicode(self).encode("utf-8")

    def __unicode__(self):
        return u"<Listen: user_name: %s, time: %s, artist_msid: %s, album_msid: %s, recording_msid: %s, artist_name: %s, track_name: %s>" % \
               (self.user_name, self.ts_since_epoch, self.artist_msid, self.album_msid, self.recording_msid, self.data['artist_name'], self.data['track_name'])
