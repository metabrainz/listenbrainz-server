from typing import Union, Optional
from uuid import UUID

import psycopg2
import psycopg2.extras
from datasethoster import Query
from flask import current_app
from markupsafe import Markup
from pydantic import BaseModel

from listenbrainz.db import similarity
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects


class SimilarRecordingsViewerInput(BaseModel):
    recording_mbids: list[UUID]
    algorithm: str


class SimilarRecordingsViewerOutputItem(BaseModel):
    artist_credit_name: Optional[str]
    recording_name: Optional[str]
    artist_credit_id: Optional[int]
    artist_credit_mbids: Optional[list[UUID]]
    recording_mbid: Optional[UUID]


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

    def fetch(self, params, offset=-1, count=-1):
        recording_mbids = params[0].recording_mbids
        algorithm = params[0].algorithm
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            references = self.get_recordings_dataset(mb_curs, ts_curs, recording_mbids)
            results = [SimilarRecordingsViewerOutputComment(comment=Markup("<p><b>Reference recording</b></p>"))]
            results.extend(references)

            similar_mbids, score_idx, mbid_idx = similarity.get(ts_curs, "recording_dev", recording_mbids, algorithm, count)
            if len(similar_mbids) == 0:
                results.append(SimilarRecordingsViewerOutputComment(comment=Markup("<p><b>No similar recordings found!</b></p>")))
                return results

            results.append(SimilarRecordingsViewerOutputComment(comment=Markup("<p><b>Similar Recordings</b></p>")))
            similar_dataset = self.get_recordings_dataset(mb_curs, ts_curs, similar_mbids, score_idx, mbid_idx)
            results.extend(similar_dataset)

            return results
