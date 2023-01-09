import psycopg2
import psycopg2.extras
from datasethoster import Query
from flask import current_app
from markupsafe import Markup

from listenbrainz.db import similarity
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects


class SimilarRecordingsViewerQuery(Query):
    """ Display similar recordings calculated using a given algorithm """

    def setup(self):
        pass

    def names(self):
        return "similar-recordings", "Similar Recordings Viewer"

    def inputs(self):
        return ['recording_mbid', 'algorithm']

    def introduction(self):
        return """This page allows you to view recordings similar to a given recording and algorithm."""

    def outputs(self):
        return None

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

        return {
            "type": "dataset",
            "columns": list(metadata[0].keys()),
            "data": metadata
        }

    def fetch(self, params, offset=-1, count=-1):
        recording_mbids = [p["recording_mbid"].strip() for p in params]
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            references = self.get_recordings_dataset(mb_curs, ts_curs, recording_mbids)
            results = [{"type": "markup", "data": Markup("<p><b>Reference recording</b></p>")}]
            results.append(references)

            similar_mbids, score_idx, mbid_idx = similarity.get(ts_curs, "recording", recording_mbids, algorithm, count)
            if len(similar_mbids) == 0:
                results.append({
                    "type": "markup",
                    "data": Markup("<p><b>No similar recordings found!</b></p>")
                })
                return results

            similar_dataset = self.get_recordings_dataset(mb_curs, ts_curs, similar_mbids, score_idx, mbid_idx)
            results.append({"type": "markup", "data": Markup("<p><b>Similar Recordings</b></p>")})
            results.append(similar_dataset)

            return results
