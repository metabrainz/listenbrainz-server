from datasethoster import Query
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class BaseMBIDMappingQuery(Query):
    """
       Thin wrapper around the MBIDMapper -- see mbid_mapper.py for details.
    """

    def __init__(self, timeout=10, remove_stop_words=True, debug=False):
        self.mapper = MBIDMapper(timeout=timeout, remove_stop_words=remove_stop_words, debug=debug)

    def outputs(self):
        return ['index', 'artist_credit_arg', 'recording_arg',
                'artist_credit_name', 'artist_mbids', 'release_name', 'recording_name',
                'release_mbid', 'recording_mbid', 'artist_credit_id', 'year']

    def get_debug_log_lines(self):
        return self.mapper.read_log()
