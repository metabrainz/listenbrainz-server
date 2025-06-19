from listenbrainz.labs_api.labs.api.similar_recordings.base import BaseSimilarRecordingsViewerQuery


class MlhdSimilarRecordingsViewerQuery(BaseSimilarRecordingsViewerQuery):
    """ Display similar recordings calculated using a given algorithm """

    def names(self):
        return "mlhd-similar-recordings", "MLHD Similar Recordings Viewer"

    def table(self):
        return "mlhd_recording_dev"

    def get_cache_key(self):
        return "labs-api:similar-recordings:mlhd"
