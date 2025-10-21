from copy import deepcopy
from datetime import datetime, timezone

import orjson


def flatten_dict(d, separator='.', parent_key=''):
    """
    Flattens a nested dictionary structure into a single dict.

    Args:
        d: dict to flatten
        separator: separator used in keys in the flattened dict (default '.')
        parent_key: prefix for all keys generated during flattening

    Returns:
        Flattened dict with keys joined by the separator
    """
    result = []
    for key, value in d.items():
        new_key = f"{parent_key}{separator if parent_key else ''}{key}"
        if isinstance(value, dict):
            result.extend(flatten_dict(value, separator, new_key).items())
        else:
            result.append((new_key, value))
    return dict(result)


def convert_comma_separated_string_to_list(string):
    if not string:
        return []
    if isinstance(string, list):
        return string
    return [val.strip() for val in string.split(',') if val.strip()]


class Listen:
    """Represents a listen object."""

    # keys we use internally for private usage
    PRIVATE_KEYS = (
        'inserted_timestamp',
    )

    # keys in additional_info that we explicitly support
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

    def __init__(self, user_id=None, user_name=None, timestamp=None,
                 recording_msid=None, inserted_timestamp=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        # Determine the timestamp and epoch seconds
        if isinstance(timestamp, (int, float)):
            self.ts_since_epoch = int(timestamp)
            self.timestamp = datetime.fromtimestamp(self.ts_since_epoch, timezone.utc)
        elif isinstance(timestamp, datetime):
            self.timestamp = timestamp
            self.ts_since_epoch = int(timestamp.timestamp())
        else:
            self.timestamp = None
            self.ts_since_epoch = None

        self.recording_msid = recording_msid
        self.inserted_timestamp = inserted_timestamp

        if data is None:
            self.data = {'additional_info': {}}
        else:
            # flatten additional_info dict if possible
            try:
                additional_info = data.get('additional_info', {})
                if isinstance(additional_info, dict):
                    flattened_data = flatten_dict(additional_info)
                    data['additional_info'] = flattened_data
            except Exception:
                # Sometimes data might be a string or not contain 'additional_info'
                pass
            self.data = data

    @classmethod
    def from_json(cls, j):
        """Factory to create Listen from a dict (usually JSON)"""
        # Try to normalize timestamp fields
        for key in ('listened_at', 'timestamp', 'ts_since_epoch'):
            if key in j:
                try:
                    ts = float(j[key])
                    listened_at = datetime.fromtimestamp(ts, timezone.utc)
                    break
                except (TypeError, ValueError):
                    pass
        else:
            listened_at = None

        return cls(
            user_id=j.get('user_id'),
            user_name=j.get('user_name'),
            timestamp=listened_at,
            recording_msid=j.get('recording_msid'),
            data=j.get('track_metadata'),
        )

    @classmethod
    def from_timescale(cls, listened_at, user_id, created, recording_msid, track_metadata,
                       recording_mbid=None, recording_name=None, release_mbid=None,
                       artist_mbids=None, ac_names=None, ac_join_phrases=None,
                       user_name=None, caa_id=None, caa_release_mbid=None):
        """Factory to create Listen from TimescaleDB row"""
        if 'additional_info' not in track_metadata:
            track_metadata['additional_info'] = {}
        track_metadata["additional_info"]["recording_msid"] = recording_msid

        if recording_mbid is not None:
            track_metadata.setdefault("mbid_mapping", {})["recording_mbid"] = str(recording_mbid)

            if recording_name is not None:
                track_metadata["mbid_mapping"]["recording_name"] = recording_name

            if release_mbid is not None:
                track_metadata["mbid_mapping"]["release_mbid"] = str(release_mbid)

            if artist_mbids and ac_names and ac_join_phrases:
                artists = []
                for mbid, name, join_phrase in zip(artist_mbids, ac_names, ac_join_phrases):
                    artists.append({
                        "artist_mbid": mbid,
                        "artist_credit_name": name,
                        "join_phrase": join_phrase,
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
            data=track_metadata,
        )

    def to_api(self):
        """
        Converts listen into API payload format.
        """
        track_metadata = deepcopy(self.data)

        data = {
            'track_metadata': track_metadata,
            'listened_at': self.ts_since_epoch,
            'recording_msid': self.recording_msid,
            'user_name': self.user_name,
            'inserted_at': int(self.inserted_timestamp.timestamp()) if self.inserted_timestamp else 0,
        }

        return data

    def to_json(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'timestamp': int(self.timestamp.timestamp()) if self.timestamp else None,
            'track_metadata': self.data,
            'recording_msid': self.recording_msid,
        }

    def to_timescale(self):
        track_metadata = deepcopy(self.data)
        if 'additional_info' not in track_metadata:
            track_metadata['additional_info'] = {}
        track_metadata['additional_info']['recording_msid'] = self.recording_msid

        # Note: original code deletes recording_msid immediately after adding it — likely a bug.
        # Removed deletion to keep recording_msid present.
        return self.timestamp, self.user_id, self.recording_msid, orjson.dumps(track_metadata).decode("utf-8")

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self))

    def __str__(self):
        return (
            f"<Listen: user_name: {self.user_name}, "
            f"time: {self.ts_since_epoch}, "
            f"recording_msid: {self.recording_msid}, "
            f"artist_name: {self.data.get('artist_name')}, "
            f"track_name: {self.data.get('track_name')}>"
        )


class NowPlayingListen:
    """Represents a now playing listen"""

    def __init__(self, user_id=None, user_name=None, data=None):
        self.user_id = user_id
        self.user_name = user_name

        if data is None:
            self.data = {'additional_info': {}}
        else:
            # 'additional_info' may not always be present in now playing listens
            additional_info = data.get('additional_info', {})
            if isinstance(additional_info, dict):
                data['additional_info'] = flatten_dict(additional_info)
            self.data = data

    def to_api(self):
        return {
            "track_metadata": self.data,
            "playing_now": True,
        }

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self))

    def __str__(self):
        return (
            f"<Now Playing Listen: user_name: {self.user_name}, "
            f"artist_name: {self.data.get('artist_name')}, "
            f"track_name: {self.data.get('track_name')}>"
        )
