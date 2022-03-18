from collections import defaultdict
from typing import Iterable, Dict, List, TypeVar
from typing import Optional, Tuple

from flask import current_app
from pydantic import BaseModel, validator
from sqlalchemy import text

from data.model.validators import check_valid_uuid
from listenbrainz.db import timescale
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


def load_recordings_from_mapping(mbids: Iterable[str], msids: Iterable[str]) -> Tuple[Dict, Dict]:
    """ Given a list of mbids and msids, returns two maps - one having mbid as key and the recording
    info as value and the other having the msid as key and recording info as value.
    """
    if not mbids and not msids:
        return {}, {}

    clauses = []
    if mbids:
        clauses.append("recording_mbid IN :mbids")
    if msids:
        clauses.append("recording_msid IN :msids")
    full_where_clause = " OR ".join(clauses)

    # direct string interpolation is susceptible to SQL injection
    # but here we are only adding where clauses with it. the actual
    # params are added using proper sqlalchemy quoting.
    query = f"""
        SELECT recording_msid::TEXT
             , recording_mbid::TEXT
             , release_mbid::TEXT
             , artist_mbids::TEXT[]
             , artist_credit_name AS artist
             , recording_name AS title
             , release_name AS release
          FROM mbid_mapping m
          JOIN mbid_mapping_metadata mm
         USING (recording_mbid)
         WHERE {full_where_clause}
    """

    with timescale.engine.connect() as connection:
        result = connection.execute(text(query), mbids=tuple(mbids), msids=tuple(msids))
        rows = result.fetchall()

        mbid_rows = {row["recording_mbid"]: dict(row) for row in rows if row["recording_mbid"] in mbids}
        msid_rows = {row["recording_msid"]: dict(row) for row in rows if row["recording_msid"] in msids}

        return mbid_rows, msid_rows


ModelT = TypeVar('ModelT', bound=MsidMbidModel)


def fetch_track_metadata_for_items(items: List[ModelT]) -> List[ModelT]:
    """ Fetches track_metadata for every object in a list of MsidMbidModel items.

        Args:
            items: the MsidMbidModel items to fetch track_metadata for.
        Returns:
            The given list of MsidMbidModel objects with updated track_metadata.
    """
    # it is possible that multiple items have same msid/mbid. for example, pinning the
    # same recording twice. since the dict is keyed by mbid/msid the corresponding value
    # should be a iterable of all items having that mbid
    msid_item_map, mbid_item_map, remaining_item_map = defaultdict(list), defaultdict(list), defaultdict(list)

    for item in items:
        if item.recording_mbid:
            mbid_item_map[item.recording_mbid].append(item)
        else:
            msid_item_map[item.recording_msid].append(item)

    # first we try to load data from mapping using mbids and msids. however, some items may
    # not have metadata in mapping. such items will be added to remaining items, and we'll
    # later lookup data for these items from messybrainz.
    mapping_mbid_metadata, mapping_msid_metadata = load_recordings_from_mapping(mbid_item_map.keys(), msid_item_map.keys())
    _update_items_from_map(mbid_item_map, mapping_mbid_metadata, remaining_item_map)
    _update_items_from_map(msid_item_map, mapping_msid_metadata, remaining_item_map)

    msid_metadatas = load_recordings_from_msids(remaining_item_map.keys())
    for metadata in msid_metadatas:
        msid = metadata["ids"]["recording_msid"]
        for item in remaining_item_map[msid]:
            item.track_metadata = {
                "track_name": metadata["payload"]["title"],
                "artist_name": metadata["payload"]["artist"],
                "additional_info": {
                    "recording_msid": msid
                }
            }

    return items


def _update_items_from_map(models: Dict[str, List[ModelT]], metadatas: Dict, remaining: Dict[str, List[ModelT]]):
    """ Updates the models in place with data of the corresponding mbid/msid from the metadatas. The models for which
    data could not be found are added to remaining items map keyed by recording_msids.
    """
    for _id, items in models.items():
        for item in items:
            # this means we could not find data for this item in the mapping tables. so we now add it to
            # remaining items map using msid as the key because this data will be looked up from messybrainz
            # afterwards.
            if _id not in metadatas:
                if item.recording_msid:
                    remaining[item.recording_msid].append(item)
                else:
                    # well we are in the weeds now. we have an item which has only mbid, its msid is None. but we
                    # couldn't find the data for the mbid in the mapping table. since msid is None, we can't lookup
                    # in messybrainz either. note that we always submit the msid from website if available so this
                    # case shouldn't occur unless some now playing case is mishandled or someone else uses the api
                    # to submit say a pinned recording with a mbid for which LB has never seen a listen.
                    # this is difficult to handle and rare, not worth to handle this until it affects someone IMO.
                    current_app.logger.critical("Couldn't find data for item in mapping and item doesn't have"
                                                f" msid: {item}")
                continue

            metadata = metadatas[_id]
            item.track_metadata = {
                "track_name": metadata["title"],
                "artist_name": metadata["artist"],
                "release_name": metadata["release"],
                "additional_info": {
                    "recording_msid": metadata["recording_msid"],
                    "recording_mbid": metadata["recording_mbid"],
                    "release_mbid": metadata["release_mbid"],
                    "artist_mbids": metadata["artist_mbids"]
                }
            }
