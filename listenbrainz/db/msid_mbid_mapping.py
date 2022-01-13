from typing import Iterable, Dict, List, TypeVar
from typing import Optional, Tuple

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
    msid_item_map, mbid_item_map = {}, {}
    for item in items:
        if item.recording_mbid:
            mbid_item_map[item.recording_mbid] = item
        else:
            msid_item_map[item.recording_msid] = item

    msid_metadatas = load_recordings_from_msids(msid_item_map.keys())
    for metadata in msid_metadatas:
        msid = metadata["ids"]["recording_msid"]
        item = msid_item_map[msid]
        item.track_metadata = {
            "track_name": metadata["payload"]["title"],
            "artist_name": metadata["payload"]["artist"],
            "additional_info": {
                "recording_msid": msid
            }
        }

    mapping_mbid_metadata, mapping_msid_metadata = load_recordings_from_mapping(mbid_item_map.keys(), msid_item_map.keys())
    _update_items_from_map(mbid_item_map, mapping_mbid_metadata)
    _update_items_from_map(msid_item_map, mapping_mbid_metadata)
    return items


def _update_items_from_map(models: Dict[str, ModelT], metadatas: Dict) -> Dict[str, ModelT]:
    for _id, item in models.items():
        if _id not in metadatas:
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

    return models
