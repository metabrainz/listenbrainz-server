from listenbrainz.labs_api.labs.api.similar_recordings.base import BaseSimilarRecordingsViewerQuery


class SimilarRecordingsViewerQuery(BaseSimilarRecordingsViewerQuery):
    """ Display similar recordings calculated using a given algorithm """

    def names(self):
        return "similar-recordings", "Similar Recordings Viewer"

    def table(self):
        return "recording_dev"

    def get_cache_key(self):
        return "labs-api:similar-recordings:listens"
