from datasethoster import Query

from listenbrainz.labs_api.labs.api.base_mbid_mapping import BaseMBIDMappingQuery
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class MBIDMappingReleaseQuery(BaseMBIDMappingQuery):
    """
       Thin wrapper around the MBIDMapper -- see mbid_mapper.py for details.
    """

    def names(self):
        return "mbid-mapping-release", "MusicBrainz ID Mapping Release lookup"

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]', '[release_name]']

    def introduction(self):
        return """Given the name of an artist, a release and the name of a recording (track)
                  this query will attempt to find a suitable match in MusicBrainz."""

    def fetch(self, params, offset=-1, count=-1):
        """ Call the MBIDMapper and carry out this mapping search """

        args = []
        for i, param in enumerate(params):
            args.append((i, param['[artist_credit_name]'], param['[recording_name]'], param['[release_name]']))

        results = []
        for index, artist_credit_name, recording_name, release_name in args:
            hit = self.mapper.search(artist_credit_name, recording_name)
            if hit:
                hit["artist_credit_arg"] = artist_credit_name
                hit["recording_arg"] = recording_name
                hit["release_arg"] = release_name
                hit["index"] = index
                results.append(hit)

        return results
