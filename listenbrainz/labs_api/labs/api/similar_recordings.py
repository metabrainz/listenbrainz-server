from datasethoster import Query
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

    def fetch(self, params, offset=-1, count=-1):
        recording_mbids = [p["recording_mbid"] for p in params]
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 10

        # resolve redirect for the given mbid if any
        references = get_recordings_from_mbids(recording_mbids)
        for r in references:
            # remove unwanted fields from output
            r.pop("original_recording_mbid", None)
            r.pop("artist_credit_id", None)
            r.pop("length", None)
            r.pop("comment", None)

        recordings = get_similar_recordings(recording_mbids, algorithm, count)

        results = [
            {
                "type": "markup",
                "data": Markup("<p><b>Reference recording</b></p>")
            },
            {
                "type": "dataset",
                "columns": list(references[0].keys()),
                "data": references
            }
        ]

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

        metadata = get_recordings_from_mbids(mbids)
        for r in metadata:
            similar_mbid = r["original_recording_mbid"]
            r["score"] = score_index[similar_mbid]
            r["reference_mbid"] = similar_mbid_index[similar_mbid]

            r.pop("original_recording_mbid", None)
            r.pop("artist_credit_id", None)
            r.pop("length", None)
            r.pop("comment", None)

        results.append({
            "type": "markup",
            "data": Markup("<p><b>Similar Recordings</b></p>")
        })
        results.append({
            "type": "dataset",
            "columns": list(metadata[0].keys()),
            "data": metadata
        })

        return results
