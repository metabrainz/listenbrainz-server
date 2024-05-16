from enum import Enum
from typing import Union, Optional
from uuid import UUID

import psycopg2
import psycopg2.extras
from datasethoster import Query, RequestSource, QueryOutputLine
from flask import current_app
from markupsafe import Markup
from pydantic import BaseModel, Field
from sqlalchemy import text

from listenbrainz.db import similarity, timescale
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects


class SimilarRecordingsViewerInput(BaseModel):
    recording_mbids: list[UUID]
    algorithm: str


class SimilarRecordingsViewerOutputItem(BaseModel):
    recording_mbid: Optional[UUID]
    recording_name: Optional[str]
    artist_credit_name: Optional[str]
    artist_credit_mbids: Optional[list[UUID]] = Field(alias="[artist_credit_mbids]")
    release_name: Optional[str]
    release_mbid: Optional[UUID]
    caa_id: Optional[int]
    caa_release_mbid: Optional[UUID]
    score: Optional[int]
    reference_mbid: Optional[UUID]


class SimilarRecordingsViewerOutputComment(BaseModel):
    comment: str


SimilarRecordingsViewerOutput = Union[SimilarRecordingsViewerOutputComment, SimilarRecordingsViewerOutputItem]


class SimilarRecordingsViewerQuery(Query):
    """ Display similar recordings calculated using a given algorithm """

    def setup(self):
        pass

    def names(self):
        return "similar-recordings", "Similar Recordings Viewer"

    def inputs(self):
        with timescale.engine.begin() as conn:
            result = conn.execute(text("""
                select distinct jsonb_object_keys(metadata) as algorithm
                  from similarity.recording_dev
            """))
            choices = {r.algorithm: r.algorithm for r in result}

        AlgorithmEnum = Enum("AlgorithmEnum", choices)

        class SimilarRecordingsViewerInput(BaseModel):
            recording_mbids: list[UUID]
            algorithm: AlgorithmEnum

        return SimilarRecordingsViewerInput

    def introduction(self):
        return """This page allows you to view recordings similar to a given recording and algorithm."""

    def outputs(self):
        return SimilarRecordingsViewerOutput

    @staticmethod
    def get_recordings_dataset(mb_curs, ts_curs, mbids, score_idx=None, similar_mbid_idx=None):
        """ Retrieve recording metadata for given list of mbids after resolving redirects, canonical redirects and
        adding similarity data if available
        """
        metadata = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, mbids)
        for r in metadata:
            if score_idx and similar_mbid_idx:
                similar_mbid = r["original_recording_mbid"]
                r["score"] = score_idx[similar_mbid]
                r["reference_mbid"] = similar_mbid_idx[similar_mbid]

            # remove unwanted fields from output
            r.pop("original_recording_mbid", None)
            r.pop("artist_credit_id", None)
            r.pop("length", None)

        return [SimilarRecordingsViewerOutputItem(**item) for item in metadata]

    def fetch(self, params, source, offset=-1, count=-1):
        recording_mbids = [str(x) for x in params[0].recording_mbids]
        algorithm = params[0].algorithm.value.strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:
            results = []

            if source == RequestSource.web:
                references = self.get_recordings_dataset(mb_curs, ts_curs, recording_mbids)
                results.append(QueryOutputLine(line=Markup("<p><b>Reference recording</b></p>")))
                results.extend(references)

            similar_mbids, score_idx, mbid_idx = similarity.get(ts_curs, "recording_dev", recording_mbids,
                                                                algorithm, count)
            if source == RequestSource.web:
                if len(similar_mbids) == 0:
                    results.append(QueryOutputLine(line=Markup("<p><b>No similar recordings found!</b></p>")))
                    return results
                else:
                    results.append(QueryOutputLine(line=Markup("<p><b>Similar Recordings</b></p>")))

            similar_dataset = self.get_recordings_dataset(mb_curs, ts_curs, similar_mbids, score_idx, mbid_idx)
            results.extend(similar_dataset)

            return results
