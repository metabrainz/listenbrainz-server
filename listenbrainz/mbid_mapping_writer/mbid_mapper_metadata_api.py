import re
from time import sleep

import typesense
import typesense.exceptions
import requests.exceptions
from markupsafe import Markup
from unidecode import unidecode
from Levenshtein import distance

from listenbrainz import config
from listenbrainz.mbid_mapping_writer.stop_words import ENGLISH_STOP_WORDS

DEFAULT_TIMEOUT = 2
COLLECTION_NAME = "canonical_musicbrainz_data_latest"
MATCH_TYPES = ('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match')
MATCH_TYPE_NO_MATCH = 0
MATCH_TYPE_LOW_QUALITY = 1
MATCH_TYPE_MED_QUALITY = 2
MATCH_TYPE_HIGH_QUALITY = 3
MATCH_TYPE_EXACT_MATCH = 4

MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE = 2
MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE = 5

ENGLISH_STOP_WORD_INDEX = {k: 1 for k in ENGLISH_STOP_WORDS}


def prepare_query(text):
    return unidecode(re.sub(" +", " ", re.sub(r'[^\w ]+', '', text)).strip().lower())


class MBIDMapperMetadataAPI:
    """
        Note: this mbid mapper version is used by the metadata api and not by the background
        mbid mapping writer process.

        This class performs a lookup of one or more artist credit name and recording name pairs
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

    def __init__(self, timeout=DEFAULT_TIMEOUT, remove_stop_words=False, debug=False):
        self.debug = debug
        self.log = []

        self.client = typesense.Client({
            'nodes': [{
                'host': config.TYPESENSE_HOST,
                'port': config.TYPESENSE_PORT,
                'protocol': 'http',
            }],
            'api_key': config.TYPESENSE_API_KEY,
            'connection_timeout_seconds': timeout
        })
        self.remove_stop_words = remove_stop_words

    def _log(self, str):
        if self.debug:
            self.log.append(str)

    def read_log(self):
        log = self.log
        self.log = []

        return log

    def detune_query_string(self, query, is_artist_credit):
        """
            Detune (remove known extra cruft) a metadata field. If a known
            trailing string exists in the input string, that string and everything
            after it is removed.
        """

        strings = ["(", "[", " ft ", " ft. ", " feat ", " feat. ", " featuring ", " - "]
        if is_artist_credit:
            strings.insert(0, ",")
            strings.append(" with ")

        for s in strings:
            index = query.find(s)
            if index >= 0:
                return query[:index].strip()

        # Yes, this is actually correct.
        return ""

    def compare(self, artist_credit_name, recording_name, artist_credit_name_hit, recording_name_hit):
        """
            Compare the fields, print debug info if turned on, and return edit distance as (a_dist, r_dist)
        """

        self._log(Markup(f"""QUERY: artist: <b>{artist_credit_name}</b> recording: <b>{recording_name}</b>"""))
        self._log(Markup(f"""HIT: artist: <b>{artist_credit_name_hit}</b> recording: <b>{recording_name_hit}</b>"""))

        return distance(artist_credit_name, artist_credit_name_hit), distance(recording_name, recording_name_hit)

    def check_hit_in_threshold(self, artist_credit_name, recording_name, ac_hit, r_hit, is_ac_detuned, is_r_detuned):
        """
            Check whether the artist and recording name found by typesense search match to the input
            artist and recording name. An exact match is performed first then falling back to a fuzzy
            match within desired threshold. The is_ac_detuned and is_r_detuned args denote whether the
            input artist and recording name are unmodified or detuned.
        """
        ac_dist, r_dist = self.compare(
            artist_credit_name,
            recording_name,
            prepare_query(ac_hit),
            prepare_query(r_hit)
        )
        match_details = Markup(f"""<b>%s</b>: ac_detuned {is_ac_detuned}, r_detuned {is_r_detuned},
        ac_dist {ac_dist:.3f} r_dist {r_dist:.3f}""")

        # If we detuned one or more fields and it matches, the best it can get is a low quality match
        if (is_ac_detuned or is_r_detuned) and \
                ac_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and \
                r_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE:
            self._log(match_details % "low quality")
            return ac_dist, r_dist, MATCH_TYPE_LOW_QUALITY

        # For exact matches, return exact match. duh.
        if ac_dist == 0 and r_dist == 0:
            self._log(match_details % "exact match")
            return ac_dist, r_dist, MATCH_TYPE_EXACT_MATCH

        # If both fields are above the high quality threshold, call it high quality
        if ac_dist <= self.MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE and \
                r_dist <= self.MATCH_TYPE_HIGH_QUALITY_MAX_EDIT_DISTANCE:
            self._log(match_details % "high quality")
            return ac_dist, r_dist, MATCH_TYPE_HIGH_QUALITY

        # If both fields are above the medium quality threshold, call it medium quality
        if ac_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and \
                r_dist <= self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE:
            self._log(match_details % "med quality")
            return ac_dist, r_dist, MATCH_TYPE_MED_QUALITY

        return ac_dist, r_dist, MATCH_TYPE_NO_MATCH

    def evaluate_hit(self, hit, artist_credit_name, recording_name, is_ac_detuned, is_r_detuned):
        """
            Evaluate the given prepared search terms and hit. If the hit doesn't match,
            attempt to detune it and try again for detuned artist and detuned recording.
            If the hit is good enough, return it, otherwise return None.
        """
        ac_hit = hit['document']['artist_credit_name']
        r_hit = hit['document']['recording_name']

        ac_hit_detuned = self.detune_query_string(ac_hit, True)
        r_hit_detuned = self.detune_query_string(r_hit, False)

        ac_dist, r_dist, match_type = self.check_hit_in_threshold(
            artist_credit_name,
            recording_name,
            ac_hit,
            r_hit,
            is_ac_detuned,
            is_r_detuned
        )
        if match_type != MATCH_TYPE_NO_MATCH:
            return hit, match_type

        # Poor results so far, lets try detuning MB ac field and try again
        if ac_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and ac_hit_detuned:
            self._log(Markup(f"""<b>no match</b>, ac_dist too high {ac_dist:.3f} continuing: detune ac"""))
            ac_dist, r_dist, match_type = self.check_hit_in_threshold(
                artist_credit_name,
                recording_name,
                ac_hit_detuned,
                r_hit,
                True,
                is_r_detuned
            )
            if match_type != MATCH_TYPE_NO_MATCH:
                return hit, match_type

        # Poor results so far, lets try detuning MB recording field and try again
        if r_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and r_hit_detuned:
            self._log(Markup(f"""<b>no match</b>, r_dist too high {r_dist:.3f} continuing: detune r"""))
            ac_dist, r_dist, match_type = self.check_hit_in_threshold(
                artist_credit_name,
                recording_name,
                ac_hit,
                r_hit_detuned,
                is_ac_detuned,
                True
            )
            if match_type != MATCH_TYPE_NO_MATCH:
                return hit, match_type

        # Poor results so far, lets try detuning both MB ac and recording field and try again
        if ac_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and ac_hit_detuned and \
                r_dist > self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE and r_hit_detuned:
            self._log(Markup(f"""<b>no match</b>, ac_dist {r_dist:.3f} and r_dist {r_dist:.3f} too high
            continuing: detune ac and r"""))
            ac_dist, r_dist, match_type = self.check_hit_in_threshold(
                artist_credit_name,
                recording_name,
                ac_hit_detuned,
                r_hit_detuned,
                True,
                True
            )
            if match_type != MATCH_TYPE_NO_MATCH:
                return hit, match_type

        self._log(Markup(f"""<b>no good match</b>, ac_dist {ac_dist:.3f}, r_dist {r_dist:.3f}, moving on"""))
        return None, MATCH_TYPE_NO_MATCH

    def lookup(self, artist_credit_name_p, recording_name_p):

        query = artist_credit_name_p + " " + recording_name_p
        if self.remove_stop_words:
            cleaned_query = []
            for word in query.split(" "):
                if word not in ENGLISH_STOP_WORD_INDEX:
                    cleaned_query.append(word)

            query = " ".join(cleaned_query)

        search_parameters = {
            'q': query,
            'query_by': "combined",
            'prefix': 'no',
            'num_typos': self.MATCH_TYPE_MED_QUALITY_MAX_EDIT_DISTANCE
        }

        while True:
            try:
                hits = self.client.collections[COLLECTION_NAME].documents.search(search_parameters)
                break
            except requests.exceptions.ReadTimeout:
                print("Got socket timeout, sleeping 5 seconds, trying again.")
                sleep(5)
            except typesense.exceptions.RequestMalformed:
                return None

        if len(hits["hits"]) == 0:
            return None

        return hits["hits"][0]

    def lookup_and_evaluate_hit(self, artist_credit_name_p, recording_name_p, is_ac_detuned, is_r_detuned):
        hit = self.lookup(artist_credit_name_p, recording_name_p)
        if not hit:
            return None

        hit, match_type = self.evaluate_hit(
            hit,
            artist_credit_name_p,
            recording_name_p,
            is_ac_detuned,
            is_r_detuned
        )
        if not hit:
            return None

        return {
            'artist_credit_name': hit['document']['artist_credit_name'],
            'artist_credit_id': hit['document']['artist_credit_id'],
            'artist_mbids': hit['document']['artist_mbids'][1:-1].split(","),
            'release_name': hit['document']['release_name'],
            'release_mbid': hit['document']['release_mbid'],
            'recording_name': hit['document']['recording_name'],
            'recording_mbid': hit['document']['recording_mbid'],
            'match_type': match_type
        }

    def search(self, artist_credit_name, recording_name):
        """
            Main query body: Prepare the search query terms and prepare
            detuned query terms. Then attempt to find the given search terms
            and if not found, sequentially try the detuned versions of the
            query terms. Return a match dict (properly formatted for this
            query) or None if not match.
        """

        artist_credit_name_p = prepare_query(artist_credit_name)
        recording_name_p = prepare_query(recording_name)

        ac_detuned = prepare_query(self.detune_query_string(artist_credit_name, True))
        r_detuned = prepare_query(self.detune_query_string(recording_name, False))
        self._log(f"ac_detuned: '{ac_detuned}' r_detuned: '{r_detuned}'")

        # lookup without any detuning
        hit = self.lookup_and_evaluate_hit(artist_credit_name_p, recording_name_p, False, False)
        if hit:
            return hit

        # lookup with only artist credit detuned
        if ac_detuned:
            self._log("Detune only artist_credit")
            hit = self.lookup_and_evaluate_hit(ac_detuned, recording_name_p, True, False)
            if hit:
                return hit

        # lookup with both artist credit and recording detuned
        if ac_detuned and r_detuned:
            self._log("Detune artist_credit and recording")
            hit = self.lookup_and_evaluate_hit(ac_detuned, r_detuned, True, True)
            if hit:
                return hit

        # this case is the last one because it didn't exist in earlier versions and
        # preserving order of cases with older versions is probably sensible.
        if r_detuned:
            self._log("Detune only recording")
            hit = self.lookup_and_evaluate_hit(artist_credit_name_p, r_detuned, False, True)
            if hit:
                return hit

        self._log("FAIL (if this is the only line of output, it means we literally have no clue what this is)")
        self._log("OK")

        return None
