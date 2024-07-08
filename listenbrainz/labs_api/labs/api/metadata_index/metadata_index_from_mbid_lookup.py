import uuid

from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.utils import lookup_using_metadata, lookup_recording_canonical_metadata


class MetadataIdFromMBIDInput(BaseModel):
    recording_mbid: uuid.UUID


class MetadataIndexFromMBIDQuery(Query):
    """ Query to lookup external service track ids using recording mbids. """

    def __init__(self, name):
        super().__init__()
        self.name = name

    def inputs(self):
        return MetadataIdFromMBIDInput

    def fetch(self, params, source, offset=-1, count=-1):
        mbids = [str(p.recording_mbid) for p in params]
        metadata = lookup_recording_canonical_metadata(mbids)
        return lookup_using_metadata(metadata, self.name, self.outputs(), f"{self.name}_track_ids")
