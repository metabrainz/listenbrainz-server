# coding=utf-8
import calendar
import time
import ujson
import yaml

from datetime import datetime
from listenbrainz.utils import escape, convert_to_unix_timestamp

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
            result.extend(list(flatten_dict(value, '.', new_key).items()))
        else:
            result.append((new_key, value))
    return dict(result)

def convert_comma_seperated_string_to_list(string):
    if not string:
        return []
    return [val for val in string.split(',')]


class Listen(object):
    """ Represents a listen object """

    # keys that we use ourselves for private usage
    PRIVATE_KEYS = (
        'inserted_timestamp',
    )

    # keys in additional_info that we support explicitly and are not superfluous
    SUPPORTED_KEYS = (
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
        'recording_msid',
    )

    TOP_LEVEL_KEYS = (
        'time',
        'user_name',
        'artist_name',
        'track_name',
        'release_name',
    )

    def __init__(self, user_id=None, user_name=None, timestamp=None, artist_msid=None, release_msid=None,
                 recording_msid=None, dedup_tag=0, inserted_timestamp=None, data=None):
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
                self.timestamp = None
                self.ts_since_epoch = None

        self.artist_msid = artist_msid
        self.release_msid = release_msid
        self.recording_msid = recording_msid
        self.dedup_tag = dedup_tag
        self.inserted_timestamp = inserted_timestamp
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

        if 'playing_now' in j:
            j.update({'listened_at': None})
        else:
            j['listened_at']=datetime.utcfromtimestamp(float(j['listened_at']))
        return cls(
            user_id=j.get('user_id'),
            user_name=j.get('user_name', ''),
            timestamp=j['listened_at'],
            artist_msid=j['track_metadata']['additional_info'].get('artist_msid'),
            release_msid=j['track_metadata']['additional_info'].get('release_msid'),
            recording_msid=j.get('recording_msid'),
            dedup_tag=j.get('dedup_tag', 0),
            data=j.get('track_metadata')
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
        track_metadata['additional_info']['release_msid'] = self.release_msid

        data = {
            'track_metadata': track_metadata,
            'listened_at': self.ts_since_epoch,
            'recording_msid': self.recording_msid,
            'user_name': self.user_name,
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


    def to_timescale(self):
        """
        Converts listen into dict that can be submitted to timescale. user_name, listened_at and recording_msid 
        are already full columns in the listens table, so we will not duplicate those values here.

        Returns:
           A JSON string

        """

        if 'tracknumber' in self.data['additional_info']:
            try:
                tracknumber = int(self.data['additional_info']['tracknumber'])
            except (ValueError, TypeError):
                tracknumber = None
        else:
            tracknumber = None

        # Collect the data to be stored in the DB, careful to not create wasteful empty fields in the JSON:
        data = {}
        if 'artist_name' in self.data and self.data['artist_name']:
            data['artist_name'] = self.data['artist_name']

        if self.artist_msid:
            data['artist_msid'] = self.artist_msid

        if 'artist_mbids' in self.data['additional_info'] and self.data['additional_info']['artist_mbids']:
            data['artist_mbids'] = ",".join(self.data['additional_info']['artist_mbids'])

        if 'release_name' in self.data and self.data['release_name']:
            data['release_name'] = self.data['release_name']

        if self.release_msid: 
            data['release_msid'] = self.release_msid

        if 'release_mbid' in self.data['additional_info'] and self.data['additional_info']['release_mbid']:
            data['release_mbid'] = self.data['additional_info']['release_mbid']

        if 'track_name' in self.data and self.data['track_name']:
            data['track_name'] = self.data['track_name']

        if 'recording_mbid' in self.data['additional_info'] and self.data['additional_info']['recording_mbid']:
            data['recording_mbid'] = self.data['additional_info']['recording_mbid']

        if 'tags' in self.data['additional_info'] and self.data['additional_info']['tags']:
            data['tags'] = ",".join(self.data['additional_info']['tags'])

        if 'release_group_mbid' in self.data['additional_info'] and self.data['additional_info']['release_group_mbid']:
            data['release_group_mbid'] = self.data['additional_info']['release_group_mbid']

        if 'track_mbid' in self.data['additional_info'] and self.data['additional_info']['track_mbid']:
            data['track_mbid'] = self.data['additional_info']['track_mbid']

        if 'work_mbids' in self.data['additional_info'] and self.data['additional_info']['work_mbids']:
            data['work_mbids'] = ','.join(self.data['additional_info']['work_mbids'])

        if tracknumber:
            data['tracknumber'] = tracknumber

        if 'isrc' in self.data['additional_info'] and self.data['additional_info']['isrc']:
            data['isrc'] = self.data['additional_info']['isrc']

        if 'spotify_id' in self.data['additional_info'] and self.data['additional_info']['spotify_id']:
            data['spotify_id'] = self.data['additional_info']['spotify_id']

        # add the user generated keys present in additional info to fields
        for key, value in self.data['additional_info'].items():
            if key in Listen.PRIVATE_KEYS:
                continue
            if key not in Listen.SUPPORTED_KEYS:
                data['fields'][key] = ujson.dumps(value)

        return ujson.dumps(data)



    def validate(self):
        return (self.user_id is not None and self.timestamp is not None and self.artist_msid is not None
                and self.recording_msid is not None and self.data is not None)

    @property
    def date(self):
        return self.timestamp

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self))

    def __unicode__(self):
        return "<Listen: user_name: %s, time: %s, artist_msid: %s, release_msid: %s, recording_msid: %s, artist_name: %s, track_name: %s>" % \
               (self.user_name, self.ts_since_epoch, self.artist_msid, self.release_msid, self.recording_msid, self.data['artist_name'], self.data['track_name'])


def convert_influx_row_to_spark_row(row):
    data = {
        'listened_at': str(row['time']),
        'user_name': row['user_name'],
        'artist_msid': row['artist_msid'],
        'artist_name': row['artist_name'],
        'artist_mbids': convert_comma_seperated_string_to_list(row.get('artist_mbids', '')),
        'release_msid': row.get('release_msid'),
        'release_name': row.get('release_name', ''),
        'release_mbid': row.get('release_mbid', ''),
        'track_name': row['track_name'],
        'recording_msid': row['recording_msid'],
        'recording_mbid': row.get('recording_mbid', ''),
        'tags': convert_comma_seperated_string_to_list(row.get('tags', [])),
    }

    if 'inserted_timestamp' in row and row['inserted_timestamp'] is not None:
        data['inserted_timestamp'] = str(datetime.utcfromtimestamp(row['inserted_timestamp']))
    else:
        data['inserted_timestamp'] = str(datetime.utcfromtimestamp(0))

    return data
