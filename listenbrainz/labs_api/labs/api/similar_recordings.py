import psycopg2
import psycopg2.extras
from datasethoster import Query
from flask import current_app
from markupsafe import Markup

from listenbrainz.db.recording_similarity import get_similar_recordings
from listenbrainz.labs_api.labs.api.utils import get_recordings_from_mbids


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
    def get_recordings_dataset(mb_curs, ts_curs, mbids, score_index=None, similar_mbid_index=None):
        metadata = get_recordings_from_mbids(mb_curs, ts_curs, mbids)
        for r in metadata:
            # remove unwanted fields from output
            r.pop("original_recording_mbid", None)
            r.pop("artist_credit_id", None)
            r.pop("length", None)
            r.pop("comment", None)

            if score_index and similar_mbid_index:
                similar_mbid = r["original_recording_mbid"]
                r["score"] = score_index[similar_mbid]
                r["reference_mbid"] = similar_mbid_index[similar_mbid]

        return {
            "type": "dataset",
            "columns": list(metadata[0].keys()),
            "data": metadata
        }

    def fetch(self, params, offset=-1, count=-1):
        recording_mbids = [p["recording_mbid"] for p in params]
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 100

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:

            recordings = get_similar_recordings(recording_mbids, algorithm, count)
            references = self.get_recordings_dataset(mb_curs, ts_curs, recordings)

            results = [{"type": "markup", "data": Markup("<p><b>Reference recording</b></p>")}]
            results.append(references)

            if len(recordings) == 0:
                results.append({
                    "type": "markup",
                    "data": Markup("<p><b>No similar recordings found!</b></p>")
                })
                return results

            similar_mbid_index = {}
            score_index = {}
            mbids = []
            for r in recordings:
                similar_mbid = str(r["similar_mbid"])
                similar_mbid_index[similar_mbid] = str(r["mbid"])
                score_index[similar_mbid] = r["score"]
                mbids.append(similar_mbid)

            similar_dataset = self.get_recordings_dataset(mb_curs, ts_curs, mbids, score_index, similar_mbid_index)
            results.append({"type": "markup", "data": Markup("<p><b>Similar Recordings</b></p>")})
            results.append(similar_dataset)

            return results
