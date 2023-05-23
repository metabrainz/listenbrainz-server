#!/usr/bin/env python3
import abc
import re
from abc import ABC

import psycopg2
import psycopg2.extras
from datasethoster import Query
from unidecode import unidecode
from listenbrainz import config


class RecordingLookupBaseQuery(Query, ABC):

    def __init__(self, debug=False):
        self.debug = debug
        self.log_lines = []

    def setup(self):
        pass

    def outputs(self):
        return ['index', 'artist_credit_arg', 'recording_arg',
                'artist_credit_name', 'release_name', 'recording_name',
                'artist_credit_id', 'artist_mbids', 'release_mbid', 'recording_mbid', 'year']

    def get_debug_log_lines(self):
        lines = self.log_lines
        self.log_lines = []
        return lines

    @abc.abstractmethod
    def get_lookup_string(self, param) -> str:
        pass

    @abc.abstractmethod
    def get_table_name(self) -> str:
        pass

    def fetch(self, params, offset=-1, count=-1):
        lookup_strings = []
        string_index = {}
        for i, param in enumerate(params):
            cleaned = unidecode(re.sub(r'[^\w]+', '', self.get_lookup_string(param)).lower())
            lookup_strings.append(cleaned)
            string_index[cleaned] = i

        lookup_strings = tuple(lookup_strings)

        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
                curs.execute(f"""
                    SELECT artist_credit_name
                         , artist_credit_id
                         , artist_mbids::TEXT[]
                         , release_name
                         , release_mbid
                         , recording_name
                         , recording_mbid::TEXT
                         , year
                         , combined_lookup
                      FROM {self.get_table_name()}
                     WHERE combined_lookup IN %s""", (lookup_strings,))

                results = []
                while True:
                    data = curs.fetchone()
                    if not data:
                        break

                    data = dict(data)
                    index = string_index[data["combined_lookup"]]
                    data["recording_arg"] = params[index]["[recording_name]"]
                    data["artist_credit_arg"] = params[index]["[artist_credit_name]"]
                    if params[index].get("[release_name]") is not None:
                        data["release_name_arg"] = params[index]["[release_name]"]
                    data["index"] = index
                    results.append(data)

                    if self.debug:
                        self.log_lines.append(
                            "exact match: '%s' '%s' '%s' %s" %
                            (data['artist_credit_name'],
                             data['recording_name'],
                             data['release_name'],
                             data['recording_mbid']))

                return results
