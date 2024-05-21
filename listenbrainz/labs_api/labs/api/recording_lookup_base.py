#!/usr/bin/env python3
import abc
import re
from abc import ABC
from typing import Optional
from uuid import UUID

import psycopg2
import psycopg2.extras
from datasethoster import Query
from pydantic import BaseModel
from unidecode import unidecode
from listenbrainz import config


class RecordingLookupBaseOutput(BaseModel):
    index: int
    artist_credit_arg: str
    recording_arg: str
    artist_credit_name: Optional[str]
    release_name: Optional[str]
    recording_name: Optional[str]
    artist_credit_id: Optional[int]
    artist_mbids: Optional[list[UUID]]
    release_mbid: Optional[UUID]
    recording_mbid: Optional[UUID]


class RecordingLookupBaseQuery(Query, ABC):

    def __init__(self, debug=False):
        self.debug = debug
        self.log_lines = []

    def setup(self):
        pass

    def outputs(self):
        return RecordingLookupBaseOutput

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

    def fetch(self, params, source, offset=-1, count=-1):
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
                    param = params[index].dict()
                    data["recording_arg"] = param["recording_name"]
                    data["artist_credit_arg"] = param["artist_credit_name"]
                    if param.get("release_name") is not None:
                        data["release_name_arg"] = param.get("release_name")
                    data["index"] = index
                    results.append(RecordingLookupBaseOutput(**data))

                    if self.debug:
                        self.log_lines.append(
                            "exact match: '%s' '%s' '%s' %s" %
                            (data['artist_credit_name'],
                             data['recording_name'],
                             data['release_name'],
                             data['recording_mbid']))

                return results
