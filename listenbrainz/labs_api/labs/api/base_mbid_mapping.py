from typing import Optional
from uuid import UUID

from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class BaseMBIDMappingOutput(BaseModel):
    index: int
    artist_credit_arg: str
    recording_arg: str
    artist_credit_name: Optional[str]
    release_name: Optional[str]
    recording_name: Optional[str]
    artist_credit_id: Optional[int]
    artist_mbids: Optional[list[UUID]]
    release_mbid: Optional[UUID]
    recording_mbid: Optional[UUID]
    match_type: int


class BaseMBIDMappingQuery(Query):
    """
       Thin wrapper around the MBIDMapper -- see mbid_mapper.py for details.
    """

    def __init__(self, timeout=10, remove_stop_words=True, debug=False):
        self.mapper = MBIDMapper(timeout=timeout, remove_stop_words=remove_stop_words, debug=debug)

    def outputs(self):
        return BaseMBIDMappingOutput

    def get_debug_log_lines(self):
        return self.mapper.read_log()
