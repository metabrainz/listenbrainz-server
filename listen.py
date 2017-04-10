# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import ujson
from datetime import datetime
import calendar

def flatten_dict(d, seperator='', parent_key=''):
    """
    Flattens a nested dictionary structure into a single dict.

    Args:
        d: the dict to be flattened
        seperator: the seperator used in keys in the flattened dict
        parent_key: the key that is prefixed to all keys generated during flattening

    Returns:
        Flattened dict with keys such as key1.key2
    """
    result = []
    for key, value in d.items():
        new_key = "{}{}{}".format(parent_key, seperator, str(key))
        if isinstance(value, dict):
            result.extend(flatten_dict(value, '.', new_key).items())
        else:
            result.append((new_key, value))
    return dict(result)


class Listen(object):
    """ Represents a listen object """

    # keys in additional_info that we support explicitly and are not superfluous
    SUPPORTED_KEYS = [
        'artist_mbids',
        'release_group_mbid',
        'release_mbid',
        'recording_mbid',
        'track_mbid',
        'work_mbids',
        'tracknumber',
        'isrc',
        'spotify_id',
        'tags',
        'artist_msid',
        'release_msid',
    ]

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
            try:
                data['additional_info'] = flatten_dict(data['additional_info'])
            except TypeError:
                # TypeError may occur here because PostgresListenStore passes strings
                # to data sometimes. If that occurs, we don't need to do anything.
                pass

            self.data = data

    @classmethod
    def from_json(cls, j):
        """Factory to make Listen() objects from a dict"""
        return cls(user_id=j['user_id'],
            user_name=j.get('user_name', ""),
            timestamp=datetime.utcfromtimestamp(float(j['listened_at'])),
            artist_msid=j['track_metadata']['additional_info'].get('artist_msid'),
            album_msid=j['track_metadata']['additional_info'].get('release_msid'),
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

        # The influx row can contain many fields that are user-generated.
        # We only need to add those fields which have some value in them to additional_info.
        # Also, we need to make sure that we don't add fields like time, user_name etc. into
        # the additional_info.
        for key, value in row.items():
            if key not in ['time', 'user_name', 'recording_msid'] and value is not None:
                data[key] = value

        return cls(
            timestamp=t,
            user_name=row.get('user_name'),
            artist_msid=row.get('artist_msid'),
            recording_msid=row.get('recording_msid'),
            album_msid=row.get('album_msid'),
            data={
                'additional_info': data,
                'artist_name': row.get('artist_name'),
                'track_name': row.get('track_name'),
            }
        )

    def to_api(self):
        """
        Converts listen into the format in which listens are returned in the payload by the api
        on get_listen requests

        Returns:
            dict with fields 'track_metadata', 'listened_at' and 'recording_msid'
        """
        track_metadata = self.data.copy()
        track_metadata['additional_info']['artist_msid'] = self.artist_msid
        track_metadata['additional_info']['release_msid'] = self.album_msid

        data = {
            'track_metadata': track_metadata,
            'listened_at': self.ts_since_epoch,
            'recording_msid': self.recording_msid,
        }

        return data

    def to_json(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'timestamp': self.timestamp,
            'track_metadata': self.data,
            'recording_msid': self.recording_msid
        }

    def to_influx(self, measurement):
        """
        Converts listen into dict that can be submitted to influx directly.

        Returns:
            a dict with approriate values of measurement, time, tags and fields
        """

        data = {
            'measurement' : measurement,
            'time' : self.ts_since_epoch,
            'tags' : {
                'user_name' : self.user_name,
            },
            'fields' : {
                'artist_name' : self.data['artist_name'],
                'artist_msid' : self.artist_msid,
                'artist_mbids' : ",".join(self.data['additional_info'].get('artist_mbids', [])),
                'album_name' : self.data.get('release_name', ''),
                'album_msid' : self.album_msid,
                'album_mbid' : self.data['additional_info'].get('release_mbid', ''),
                'track_name' : self.data['track_name'],
                'recording_msid' : self.recording_msid,
                'recording_mbid' : self.data['additional_info'].get('recording_mbid', ''),
                'tags' : ",".join(self.data['additional_info'].get('tags', [])),
            }
        }

        # add the user generated keys present in additional info to fields
        for key, value in self.data['additional_info'].items():
            if key not in Listen.SUPPORTED_KEYS:
                data['fields'][key] = value

        return data

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
