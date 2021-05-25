import re
from time import sleep

import typesense
import typesense.exceptions
import requests.exceptions
from datasethoster import Query
from unidecode import unidecode
from Levenshtein import distance

from listenbrainz import config

DEFAULT_TIMEOUT=2
COLLECTION_NAME = "mbid_mapping_latest"
MATCH_TYPES = ('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match')
MATCH_TYPE_NO_MATCH = 0
MATCH_TYPE_LOW_QUALITY = 1
MATCH_TYPE_MED_QUALITY = 2
MATCH_TYPE_HIGH_QUALITY = 3
MATCH_TYPE_EXACT_MATCH = 4

MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE = 2
MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE = 5


def prepare_query(text):
    return unidecode(re.sub(" +", " ", re.sub(r'[^\w ]+', '', text)).lower())


class MBIDMappingQuery(Query):
    """
        This query performs a lookup of one or more artist credit name and recording name pairs
        to find the best possible match in MusicBrainz. This query will unaccent query
        parameters, be resistant to typos and attempt to modify the search parameters
        in effort to find a best match.

        For instance, if "Glory Box feat. Sloppy Jo" isn't matched, it will try to match "Glory Box".
        It is the caller's responsibility to ensure that the results meet the criteria for the
        given task. This mapping lookup aims to find a match by a number of means necessary that
        may or may not be acceptable to the caller.

        Other possible detunings:
        - Swap artist/recording
        - remove track numbers from recording

        Overall these detunings and edit distances will need more tuning as we start using this
        endpoint for our MessyBrainz mapping. For this reason the debug flag and optional
        debug output remains since more debugging/tuning will need to be done later on.
    """

    MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE = 2
    MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE = 5

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.debug = False

        self.client = typesense.Client({
            'nodes': [{
                'host': config.TYPESENSE_HOST,
                'port': config.TYPESENSE_PORT,
                'protocol': 'http',
            }],
            'api_key': config.TYPESENSE_API_KEY,
            'connection_timeout_seconds': timeout
        })

    def names(self):
        return ("mbid-mapping", "MusicBrainz ID Mapping lookup")

    def inputs(self):
        return ['[artist_credit_name]', '[recording_name]']

    def introduction(self):
        return """Given the name of an artist and the name of a recording (track)
                  this query will attempt to find a suitable match in MusicBrainz."""

    def outputs(self):
        return ['index', 'artist_credit_arg', 'recording_arg',
                'artist_credit_name', 'release_name', 'recording_name',
                'release_mbid', 'recording_mbid', 'artist_credit_id']

    def fetch(self, params, offset=-1, count=-1):
        """ Main entry point for the query """

        args = []
        for i, param in enumerate(params):
            args.append((i, param['[artist_credit_name]'],
                         param['[recording_name]']))

        results = []
        for index, artist_credit_name, recording_name in args:
            hit = self.search(artist_credit_name, recording_name)
            if hit:
                hit["artist_credit_arg"] = artist_credit_name
                hit["recording_arg"] = recording_name
                hit["index"] = index
                results.append(hit)

        return results

    def detune_query_string(self, query):
        """
            Detune (remove known extra cruft) a metadata field. If a known
            trailing string exists in the input string, that string and everything
            after it is removed.
        """

        for s in ("(", "[", " ft ", " ft. ", " feat ", " feat. ", " featuring "):
            index = query.find(s)
            if index >= 0:
                return query[:index].strip()

        return ""

    def compare(self, artist_credit_name, recording_name, artist_credit_name_hit, recording_name_hit):
        """
            Compare the fields, print debug info if turned on, and return edit distance as (a_dist, r_dist)
        """

        if self.debug:
            print("Q %-60s %-60s" %
                  (artist_credit_name[:59], recording_name[:59]))
            print("H %-60s %-60s" %
                  (artist_credit_name_hit[:59], recording_name_hit[:59]))

        return (distance(artist_credit_name, artist_credit_name_hit), distance(recording_name, recording_name_hit))

    def evaluate_hit(self, hit, artist_credit_name, recording_name):
        """
            Evaluate the given prepared search terms and hit. If the hit doesn't match,
            attempt to detune it and try again for detuned artist and detuned recording.
            If the hit is good enough, return it, otherwise return None.
        """
        ac_hit = hit['document']['artist_credit_name']
        r_hit = hit['document']['recording_name']

        ac_detuned = self.detune_query_string(ac_hit)
        r_detuned = self.detune_query_string(r_hit)

        is_ac_detuned = False
        is_r_detuned = False
        while True:
            ac_dist, r_dist = self.compare(
                artist_credit_name, recording_name, prepare_query(ac_hit), prepare_query(r_hit))

            # If we detuned one or more fields and it matches, the best it can get is a low quality match
            if (is_ac_detuned or is_r_detuned) and ac_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and r_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE:
                return (hit, MATCH_TYPE_LOW_QUALITY)

            # For exact matches, return exact match. duh.
            if ac_dist == 0 and r_dist == 0:
                return (hit, MATCH_TYPE_EXACT_MATCH)

            # If both fields are above the high quality threshold, call it high quality
            if ac_dist <= self.MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE and r_dist <= self.MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE:
                return (hit, MATCH_TYPE_HIGH_QUALITY)

            # If both fields are above the medium quality threshold, call it medium quality
            if ac_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and r_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE:
                return (hit, MATCH_TYPE_MED_QUALITY)

            # Poor results so far, lets try detuning fields and try again
            if ac_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and ac_detuned:
                ac_hit = ac_detuned
                ac_detuned = ""
                is_ac_detuned = True
                continue

            if r_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and r_detuned:
                r_hit = r_detuned
                r_detuned = ""
                is_r_detuned = True
                continue

            return (None, MATCH_TYPE_NO_MATCH)

    def lookup(self, artist_credit_name_p, recording_name_p):

        search_parameters = {
            'q': artist_credit_name_p + " " + recording_name_p,
            'query_by': "combined",
            'prefix': 'no',
            'num_typos': self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE
        }

        while True:
            try:
                hits = self.client.collections[COLLECTION_NAME].documents.search(
                    search_parameters)
                break
            except requests.exceptions.ReadTimeout:
                print("Got socket timeout, sleeping 5 seconds, trying again.")
                sleep(5)

        if len(hits["hits"]) == 0:
            return None

        return hits["hits"][0]

    def search(self, artist_credit_name, recording_name):
        """
            Main query body: Prepare the search query terms and prepare
            detuned query terms. Then attempt to find the given search terms
            and if not found, sequentially try the detuned versions of the
            query terms. Return a match dict (properly formatted for this
            query) or None if not match.
        """

        if self.debug:
            print("- %-60s %-60s" %
                  (artist_credit_name[:59], recording_name[:59]))

        artist_credit_name_p = prepare_query(artist_credit_name)
        recording_name_p = prepare_query(recording_name)

        ac_detuned = prepare_query(
            self.detune_query_string(artist_credit_name_p))
        r_detuned = prepare_query(self.detune_query_string(recording_name_p))

        while True:
            hit = self.lookup(artist_credit_name_p, recording_name_p)
            if hit:
                (hit, match_type) = self.evaluate_hit(
                    hit, artist_credit_name_p, recording_name_p)

            if not hit:
                hit = None
                if ac_detuned:
                    artist_credit_name_p = ac_detuned
                    ac_detuned = None
                    continue

                if r_detuned:
                    recording_name_p = r_detuned
                    r_detuned = None
                    continue

                if self.debug:
                    print("FAIL.\n")

                return None

            break

        if self.debug:
            print("OK.\n")

        return {'artist_credit_name': hit['document']['artist_credit_name'],
                'artist_credit_id': hit['document']['artist_credit_id'],
                'release_name': hit['document']['release_name'],
                'release_mbid': hit['document']['release_mbid'],
                'recording_name': hit['document']['recording_name'],
                'recording_mbid': hit['document']['recording_mbid'],
                'match_type': match_type }
