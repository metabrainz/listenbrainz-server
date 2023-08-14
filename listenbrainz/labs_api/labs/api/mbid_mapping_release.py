from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.base_mbid_mapping import BaseMBIDMappingQuery, BaseMBIDMappingOutput


class MBIDMappingReleaseInput(BaseModel):
    artist_credit_name: str
    recording_name: str
    release_name: str


class MBIDMappingReleaseQuery(BaseMBIDMappingQuery):
    """
       Thin wrapper around the MBIDMapper -- see mbid_mapper.py for details.
    """

    def names(self):
        return "mbid-mapping-release", "MusicBrainz ID Mapping Release lookup"

    def inputs(self):
        return MBIDMappingReleaseInput

    def introduction(self):
        return """Given the name of an artist, a release and the name of a recording (track)
                  this query will attempt to find a suitable match in MusicBrainz."""

    def fetch(self, params, source, offset=-1, count=-1):
        """ Call the MBIDMapper and carry out this mapping search """

        args = []
        for i, param in enumerate(params):
            args.append((i, param.artist_credit_name, param.recording_name, param.release_name))

        results = []
        for index, artist_credit_name, recording_name, release_name in args:
            hit = self.mapper.search(artist_credit_name, recording_name, release_name)
            if hit:
                hit["artist_credit_arg"] = artist_credit_name
                hit["recording_arg"] = recording_name
                hit["release_arg"] = release_name
                hit["index"] = index
                results.append(hit)

        return [BaseMBIDMappingOutput(**row) for row in results]
