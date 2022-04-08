from datasethoster import Query
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class MBIDMappingQuery(Query):
    """
       Thin wrapper around the MBIDMapper -- see mbid_mapper.py for details.
    """

    def __init__(self, timeout=10, remove_stop_words=True, debug=False):
        self.mapper = MBIDMapper(timeout=timeout, remove_stop_words=remove_stop_words, debug=debug)

    def names(self):
        return ("mbid-mapping", "MusicBrainz ID Mapping lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """Given the name of an artist and the name of a recording (track)
                  this query will attempt to find a suitable match in MusicBrainz."""

    def outputs(self):
        return ['index', 'artist_credit_arg', 'recording_arg',
                'artist_credit_name', 'artist_mbids', 'release_name', 'recording_name',
                'release_mbid', 'recording_mbid', 'artist_credit_id', 'year']

    def get_debug_log_lines(self):
        return self.mapper.read_log()

    def fetch(self, params, offset=-1, count=-1):
        """ Call the MBIDMapper and carry out this mapping search """

        args = []
        for i, param in enumerate(params):
            args.append((i, param['[artist_credit_name]'],
                         param['[recording_name]']))

        results = []
        for index, artist_credit_name, recording_name in args:
            hit = self.mapper.search(artist_credit_name, recording_name)
            if hit:
                hit["artist_credit_arg"] = artist_credit_name
                hit["recording_arg"] = recording_name
                hit["index"] = index
                results.append(hit)

        return results
