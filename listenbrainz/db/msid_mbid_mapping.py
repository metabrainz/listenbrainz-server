from collections import defaultdict
from typing import List, TypeVar
from typing import Optional

from flask import current_app
from psycopg2.extras import DictCursor
from pydantic import BaseModel, validator, root_validator

from data.model.validators import check_valid_uuid
from listenbrainz.db.recording import load_recordings_from_mbids
from listenbrainz.messybrainz import load_recordings_from_msids


class MsidMbidModel(BaseModel):
    """
    A model to use as base for tables which support both msid and mbids.

    We intend to migrate from msids to mbids but for compatibility and till
    the remaining gaps in mapping are filled we want to support msids as well.
    """
    recording_msid: Optional[str]
    recording_mbid: Optional[str]
    track_metadata: dict = None

    _validate_msids: classmethod = validator(
        "recording_msid",
        "recording_mbid",
        allow_reuse=True
    )(check_valid_uuid)

    @root_validator
    def check_at_least_mbid_or_msid(cls, values):
        recording_msid, recording_mbid = values.get('recording_msid'), values.get('recording_mbid')
        if recording_msid is None and recording_mbid is None:
            raise ValueError("at least one of recording_msid or recording_mbid should be specified")
        return values


ModelT = TypeVar('ModelT', bound=MsidMbidModel)


def fetch_track_metadata_for_items(ts_conn, items: List[ModelT]) -> List[ModelT]:
    """ Fetches track_metadata for every object in a list of MsidMbidModel items.

        Args:
            ts_conn: timescale database connection
            items: the MsidMbidModel items to fetch track_metadata for.
        Returns:
            The given list of MsidMbidModel objects with updated track_metadata.
    """
    # it is possible that multiple items have same msid/mbid. for example, pinning the
    # same recording twice. since the dict is keyed by mbid/msid the corresponding value
    # should be a iterable of all items having that mbid
    msid_item_map, mbid_item_map = defaultdict(list), defaultdict(list)

    for item in items:
        if item.recording_mbid:
            mbid_item_map[item.recording_mbid].append(item)
        else:
            msid_item_map[item.recording_msid].append(item)

    # first we try to load data from mapping using mbids. for the items without a mbid,
    # we'll later lookup data for these items from messybrainz.
    with ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_curs:
        mbid_metadatas = load_recordings_from_mbids(ts_curs, mbid_item_map.keys())
        _update_mbid_items(mbid_item_map, mbid_metadatas, msid_item_map)

        msid_metadatas = load_recordings_from_msids(ts_curs, msid_item_map.keys())
        _update_msid_items(msid_item_map, msid_metadatas)

    return items


def _update_mbid_items(models: dict[str, list[ModelT]], metadatas: dict, remaining: dict[str, list[ModelT]]):
    """ Updates the models in place with data of the corresponding mbid from the metadata. The models for which
    data could not be found are added to a map keyed by recording_msids.
    """
    for mbid, items in models.items():
        metadata = metadatas.get(mbid)
        for item in items:
            # this means we could not find data for this item in the mapping tables. so we now add it to
            # remaining items map using msid as the key because this data will be looked up from messybrainz
            # afterwards.
            if not metadata:
                if item.recording_msid:
                    remaining[item.recording_msid].append(item)
                else:
                    # well we are in the weeds now. we have an item which has only mbid, its msid is None. but we
                    # couldn't find the data for the mbid in the mapping table. since msid is None, we can't lookup
                    # in messybrainz either. note that we always submit the msid from website if available so this
                    # case shouldn't occur unless some now playing case is mishandled or someone else uses the api
                    # to submit say a pinned recording with a mbid for which LB has never seen a listen.
                    current_app.logger.warning("Couldn't find data for item in mapping and item doesn't have"
                                               " msid: %s", item)
                continue

            item.track_metadata = {
                "track_name": metadata["title"],
                "artist_name": metadata["artist"],
                "release_name": metadata["release"],
                "mbid_mapping": {
                    "recording_mbid": metadata["recording_mbid"],
                    "release_mbid": metadata["release_mbid"],
                    "artist_mbids": metadata["artist_mbids"],
                    "artists": metadata["artists"]
                }
            }

            if metadata["caa_id"]:
                item.track_metadata["mbid_mapping"]["caa_id"] = metadata["caa_id"]
                item.track_metadata["mbid_mapping"]["caa_release_mbid"] = metadata["caa_release_mbid"]

            if item.recording_msid:
                item.track_metadata["additional_info"] = {"recording_msid": item.recording_msid}


def _update_msid_items(models: dict[str, list[ModelT]], metadatas: dict[str, dict]):
    """ Updates the models in place with data of the corresponding msid from the metadata. """
    for msid, items in models.items():
        # we don't validate recording msids submitted in feedback or pinned recordings,
        # so it is possible for anyone to submit a non-existent msid.
        metadata = metadatas.get(msid)
        if not metadata:
            continue

        for item in items:
            item.track_metadata = {
                "track_name": metadata["title"],
                "artist_name": metadata["artist"],
                "additional_info": {
                    "recording_msid": msid
                }
            }

            if metadata.get("release"):
                item.track_metadata["release_name"] = metadata["release"]
