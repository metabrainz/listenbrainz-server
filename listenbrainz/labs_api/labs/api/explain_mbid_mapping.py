from datasethoster import Query
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper


class ExplainMBIDMappingQuery(Query):
    """
       Thin wrapper around the MBIDMapper used in printing the debug info for a mapping 
    """

    def __init__(self, remove_stop_words=False):
        self.mapper = MBIDMapper(remove_stop_words=remove_stop_words, debug=True)

    def names(self):
        return ("explain-mbid-mapping", "Explain MusicBrainz ID Mapping lookup")

    def inputs(self):
        return ['artist_credit_name', 'recording_name']

    def introduction(self):
        return """Given the name of an artist and the name of a recording (track)
                  this uery execute the mapping and print its debug log"""

    def outputs(self):
        return ['log_lines']

    def fetch(self, params, offset=-1, count=-1):
        """ Call the MBIDMapper and carry out this mapping search """

        results = []
        self.mapper.search(params[0]["artist_credit_name"], params[0]["recording_name"])
        for line in self.mapper.read_log():
            results.append({"log_lines": line})

        return results
