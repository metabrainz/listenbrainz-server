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
        recording_mbid = params[0]["recording_mbid"].strip()
        algorithm = params[0]["algorithm"].strip()
        count = count if count > 0 else 100

        # resolve redirect for the given mbid if any
        reference = get_recordings_from_mbids([recording_mbid])[0]
        # remove unwanted fields from output
        reference.pop("original_recording_mbid", None)
        reference.pop("artist_credit_id", None)

        recordings = get_similar_recordings(reference["recording_mbid"], algorithm, count)

        results = [
            {
                "type": "markup",
                "data": Markup("<p><b>Reference recording</b></p>")
            },
            {
                "type": "dataset",
                "columns": list(reference.keys()),
                "data": [reference]
            }
        ]

        if len(recordings) == 0:
            results.append({
                "type": "markup",
                "data": Markup("<p><b>No similar recordings found!</b></p>")
            })
            return results

        index = {}
        mbids = []
        for r in recordings:
            mbid = str(r.similar_mbid)
            index[mbid] = r.score
            mbids.append(mbid)

        metadata = get_recordings_from_mbids(mbids)
        for r in metadata:
            r["score"] = index[r["original_recording_mbid"]]
            r.pop("original_recording_mbid", None)
            r.pop("artist_credit_id", None)

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
