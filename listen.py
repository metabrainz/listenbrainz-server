# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ujson
from datetime import datetime
import calendar

class Listen(object):
    """ Represents a listen object """
    def __init__(self, user_id=None, user_name=None, timestamp=None, artist_msid=None, album_msid=None,
                 recording_msid=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        # determine the type of timestamp and do the right thing
        if isinstance(timestamp, int) or isinstance(timestamp, float):
            self.ts_since_epoch = int(timestamp)
            self.timestamp = datetime.utcfromtimestamp(self.ts_since_epoch)
        else:
            if timestamp:
                self.timestamp = timestamp
                self.ts_since_epoch = calendar.timegm(self.timestamp.utctimetuple())
            else:
                self.timestamp = 0
                self.ts_since_epoch = 0

        self.artist_msid = artist_msid
        self.album_msid = album_msid
        self.recording_msid = recording_msid
        if data is None:
            self.data = {'additional_info': {}}
        else:
            self.data = data

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

    @classmethod
    def from_influx(cls, row):
        """ Factory to make Listen objects from an influx row
        """
        dt = datetime.strptime(row['time'] , '%Y-%m-%dT%H:%M:%SZ')
        t = int(dt.strftime('%s'))
        mbids = []
        artist_mbids = row.get('artist_mbids')
        if artist_mbids:
            for mbid in artist_mbids.split(','):
                mbids.append(mbid)

        tags = []
        influx_tags = row.get('tags')
        if influx_tags:
            for tag in influx_tags.split(','):
                tags.append(tag)

        data = {
            'artist_mbids': mbids,
            'album_msid': row.get('album_msid'),
            'album_mbid': row.get('album_mbid'),
            'album_name': row.get('album_name'),
            'recording_mbid': row.get('recording_mbid'),
            'tags': tags,
        }
        return cls(
            timestamp=t,
            user_name=row.get('user_name'),
            artist_msid=row.get('artist_msid'),
            recording_msid=row.get('recording_msid'),
            data={
                'additional_info': data,
                'artist_name': row.get('artist_name'),
                'track_name': row.get('track_name'),
            }
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
