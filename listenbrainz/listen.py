from copy import deepcopy
from datetime import datetime, timezone

import orjson


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
    if isinstance(string, list):
        return string
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
        'recording_msid',
        'duration_ms',
        'duration',
    )

    TOP_LEVEL_KEYS = (
        'time',
        'user_name',
        'artist_name',
        'track_name',
        'release_name',
    )

    def __init__(self, user_id=None, user_name=None, timestamp=None, recording_msid=None, inserted_timestamp=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        # determine the type of timestamp and do the right thing
        if isinstance(timestamp, int) or isinstance(timestamp, float):
            self.ts_since_epoch = int(timestamp)
            self.timestamp = datetime.fromtimestamp(self.ts_since_epoch, timezone.utc)
        else:
            if timestamp:
                self.timestamp = timestamp
                self.ts_since_epoch = int(self.timestamp.timestamp())
            else:
                self.timestamp = None
                self.ts_since_epoch = None

        self.recording_msid = recording_msid
        self.inserted_timestamp = inserted_timestamp
        if data is None:
            self.data = {'additional_info': {}}
        else:
            try:
                flattened_data = flatten_dict(data['additional_info'])
                data['additional_info'] = flattened_data
            except TypeError:
                # TypeError may occur here because PostgresListenStore passes strings
                # to data sometimes. If that occurs, we don't need to do anything.
                pass

            self.data = data

    @classmethod
    def from_json(cls, j):
        """Factory to make Listen() objects from a dict"""
        # Let's go play whack-a-mole with our lovely whicket of timestamp fields. Hopefully one will work!
        try:
            j['listened_at'] = datetime.fromtimestamp(float(j['listened_at']), timezone.utc)
        except KeyError:
            try:
                j['listened_at'] = datetime.fromtimestamp(float(j['timestamp']), timezone.utc)
            except KeyError:
                j['listened_at'] = datetime.fromtimestamp(float(j['ts_since_epoch']), timezone.utc)

        return cls(
            user_id=j.get('user_id'),
            user_name=j.get('user_name'),
            timestamp=j['listened_at'],
            recording_msid=j.get('recording_msid'),
            data=j.get('track_metadata')
        )

    @classmethod
    def from_timescale(cls, listened_at, user_id, created, recording_msid, track_metadata,
                       recording_mbid=None, recording_name=None, release_mbid=None, artist_mbids=None,
                       ac_names=None, ac_join_phrases=None, user_name=None,
                       caa_id=None, caa_release_mbid=None):
        """Factory to make Listen() objects from a timescale dict"""
        track_metadata["additional_info"]["recording_msid"] = recording_msid
        if recording_mbid is not None:
            track_metadata["mbid_mapping"] = {"recording_mbid": str(recording_mbid)}

            if recording_name is not None:
                track_metadata["mbid_mapping"]["recording_name"] = recording_name

            if release_mbid is not None:
                track_metadata["mbid_mapping"]["release_mbid"] = str(release_mbid)

            if artist_mbids is not None and ac_names is not None and ac_join_phrases is not None:
                artists = []
                for (mbid, name, join_phrase) in zip(artist_mbids, ac_names, ac_join_phrases):
                    artists.append({
                        "artist_mbid": mbid,
                        "artist_credit_name": name,
                        "join_phrase": join_phrase
                    })

                track_metadata["mbid_mapping"]["artists"] = artists
                track_metadata["mbid_mapping"]["artist_mbids"] = [str(m) for m in artist_mbids]

            if caa_id is not None and caa_release_mbid is not None:
                track_metadata["mbid_mapping"]["caa_id"] = caa_id
                track_metadata["mbid_mapping"]["caa_release_mbid"] = caa_release_mbid

        return cls(
            user_id=user_id,
            user_name=user_name,
            timestamp=listened_at,
            recording_msid=recording_msid,
            inserted_timestamp=created,
            data=track_metadata
        )

    def to_api(self):
        """
        Converts listen into the format in which listens are returned in the payload by the api
        on get_listen requests

        Returns:
            dict with fields 'track_metadata', 'listened_at' and 'recording_msid'
        """
        track_metadata = self.data.copy()

        data = {
            'track_metadata': track_metadata,
            'listened_at': self.ts_since_epoch,
            'recording_msid': self.recording_msid,
            'user_name': self.user_name,
            'inserted_at': int(self.inserted_timestamp.timestamp()) if self.inserted_timestamp else 0
        }

        return data

    def to_json(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'timestamp': int(self.timestamp.timestamp()) if self.timestamp else None,
            'track_metadata': self.data,
            'recording_msid': self.recording_msid
        }

    def to_timescale(self):
        track_metadata = deepcopy(self.data)
        track_metadata['additional_info']['recording_msid'] = self.recording_msid
        del track_metadata['additional_info']['recording_msid']
        return self.timestamp, self.user_id, self.recording_msid, orjson.dumps(track_metadata).decode("utf-8")

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self))

    def __unicode__(self):
        return "<Listen: user_name: %s, time: %s, recording_msid: %s, artist_name: %s, track_name: %s>" % \
               (self.user_name, self.ts_since_epoch, self.recording_msid, self.data['artist_name'], self.data['track_name'])


class NowPlayingListen:
    """Represents a now playing listen"""

    def __init__(self, user_id=None, user_name=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        if data is None:
            self.data = {'additional_info': {}}
        else:
            # submitted listens always has an additional_info key in track_metadata
            # because of the msb lookup. now playing listens do not have a msb lookup
            # so the additional_info key may not always be present.
            additional_info = data.get('additional_info', {})
            data['additional_info'] = flatten_dict(additional_info)
            self.data = data

    def to_api(self):
        return {
            "track_metadata": self.data,
            "playing_now": True
        }

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self))

    def __str__(self):
        return "<Now Playing Listen: user_name: %s, artist_name: %s, track_name: %s>" % \
               (self.user_name, self.data['artist_name'], self.data['track_name'])
