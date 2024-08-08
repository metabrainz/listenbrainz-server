from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.utils import lookup_using_metadata


class MetadataIndexFromMetadataInput(BaseModel):
    artist_name: str
    release_name: str
    track_name: str


class MetadataIndexFromMetadataQuery(Query):
    """ Query to lookup external service track ids using artist name, release name and track name. """

    def __init__(self, name):
        super().__init__()
        self.name = name

    def inputs(self):
        return MetadataIndexFromMetadataInput

    def fetch(self, params, source, offset=-1, count=-1):
        data = [p.dict() for p in params]
        return lookup_using_metadata(data, self.name, self.outputs(), f"{self.name}_track_ids")
