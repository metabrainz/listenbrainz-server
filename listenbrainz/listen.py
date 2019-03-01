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

    @classmethod
    def from_influx(cls, row):
        """ Factory to make Listen objects from an influx row
        """


        t = convert_to_unix_timestamp(row['time'])

        data = {
            'release_msid': row.get('release_msid'),
            'release_mbid': row.get('release_mbid'),
            'recording_mbid': row.get('recording_mbid'),
            'release_group_mbid': row.get('release_group_mbid'),
            'artist_mbids': convert_comma_seperated_string_to_list(row.get('artist_mbids', '')),
            'tags': convert_comma_seperated_string_to_list(row.get('tags', '')),
            'work_mbids': convert_comma_seperated_string_to_list(row.get('work_mbids', '')),
            'isrc': row.get('isrc'),
            'spotify_id': row.get('spotify_id'),
            'tracknumber': row.get('tracknumber'),
            'track_mbid': row.get('track_mbid'),
        }

        # The influx row can contain many fields that are user-generated.
        # We only need to add those fields which have some value in them to additional_info.
        # Also, we need to make sure that we don't add fields like time, user_name etc. into
        # the additional_info.
        for key, value in row.items():
            if key not in data and key not in Listen.TOP_LEVEL_KEYS + Listen.PRIVATE_KEYS and value is not None:
                try:
                    value = ujson.loads(value)
                    data[key] = value
                    continue
                except (ValueError, TypeError):
                    pass

                # there are some lists in the database that were converted to string
                # via str(list) so they can't be loaded via json.
                # Example: "['Blank & Jones']"
                # However, yaml parses them safely and correctly
                try:
                    value = yaml.safe_load(value)
                    data[key] = value
                    continue
                except (ValueError, yaml.scanner.ScannerError, yaml.parser.ParserError, Exception):
                    pass

                data[key] = value

        return cls(
            timestamp=t,
            user_name=row.get('user_name'),
            artist_msid=row.get('artist_msid'),
            recording_msid=row.get('recording_msid'),
            release_msid=row.get('release_msid'),
            inserted_timestamp=row.get('inserted_timestamp'),
            data={
                'additional_info': data,
                'artist_name': row.get('artist_name'),
                'track_name': row.get('track_name'),
                'release_name': row.get('release_name'),
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
        track_metadata['additional_info']['release_msid'] = self.release_msid

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
            a dict with appropriate values of measurement, time, tags and fields
        """

        data = {
            'measurement' : measurement,
            'time' : self.ts_since_epoch,
            'fields' : {
                'user_name' : escape(self.user_name),
                'artist_name' : self.data['artist_name'],
                'artist_msid' : self.artist_msid,
                'artist_mbids' : ",".join(self.data['additional_info'].get('artist_mbids', [])),
                'release_name' : self.data.get('release_name', ''),
                'release_msid' : self.release_msid,
                'release_mbid' : self.data['additional_info'].get('release_mbid', ''),
                'track_name' : self.data['track_name'],
                'recording_msid' : self.recording_msid,
                'recording_mbid' : self.data['additional_info'].get('recording_mbid', ''),
                'tags' : ",".join(self.data['additional_info'].get('tags', [])),
                'release_group_mbid': self.data['additional_info'].get('release_group_mbid', ''),
                'track_mbid': self.data['additional_info'].get('track_mbid', ''),
                'work_mbids': ','.join(self.data['additional_info'].get('work_mbids', [])),
                'tracknumber': self.data['additional_info'].get('tracknumber', ''),
                'isrc': self.data['additional_info'].get('isrc', ''),
                'spotify_id': self.data['additional_info'].get('spotify_id', ''),
                'inserted_timestamp': int(time.time()),
            }
        }


        # if we need a dedup tag, then add it to the row
        if self.dedup_tag > 0:
            data['tags'] = {'dedup_tag': self.dedup_tag}

        # add the user generated keys present in additional info to fields
        for key, value in self.data['additional_info'].items():
            if key in Listen.PRIVATE_KEYS:
                continue
            if key not in Listen.SUPPORTED_KEYS:
                data['fields'][key] = ujson.dumps(value)

        return data



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
    return {
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
