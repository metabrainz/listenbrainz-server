from typing import Optional, Union
from uuid import UUID

from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class ExplainMBIDMappingInput(BaseModel):
    artist_credit_name: str
    recording_name: str
    release_name: Optional[str]


class ExplainMBIDMappingOutputLog(BaseModel):
    log_lines: str


class ExplainMBIDMappingOutputItem(BaseModel):
    artist_credit_name: Optional[str]
    release_name: Optional[str]
    recording_name: Optional[str]
    artist_credit_id: Optional[int]
    artist_mbids: Optional[list[UUID]]
    release_mbid: Optional[UUID]
    recording_mbid: Optional[UUID]
    year: Optional[int]


ExplainMBIDMappingOutput = Union[ExplainMBIDMappingOutputItem, ExplainMBIDMappingOutputLog]


class ExplainMBIDMappingQuery(Query):
    """
       Thin wrapper around the MBIDMapper used in printing the debug info for a mapping 
    """

    def __init__(self, remove_stop_words=True):
        self.mapper = MBIDMapper(remove_stop_words=remove_stop_words, debug=True)

    def names(self):
        return "explain-mbid-mapping", "Explain MusicBrainz ID Mapping lookup"

    def inputs(self):
        return ExplainMBIDMappingInput

    def introduction(self):
        return """Given the name of an artist and the name of a recording (track)
                  this uery execute the mapping and print its debug log"""

    def outputs(self):
        return ExplainMBIDMappingOutput

    def fetch(self, params, source, offset=-1, count=-1):
        """ Call the MBIDMapper and carry out this mapping search """
        hit = self.mapper.search(params[0].artist_credit_name, params[0].recording_name, params[0].release_name)
        results: list = [ExplainMBIDMappingOutputLog(log_lines=line) for line in self.mapper.read_log()]
        if hit:
            results.append(ExplainMBIDMappingOutputItem(**hit))
        return results
