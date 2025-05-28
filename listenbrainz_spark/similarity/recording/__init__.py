from listenbrainz_spark.similarity.recording.listens import ListensRecordingSimilarity
from listenbrainz_spark.similarity.recording.mlhd import MlhdRecordingSimilarity


def main(mlhd, **kwargs):
    """ Generate similar recordings """
    if mlhd:
        engine = MlhdRecordingSimilarity(**kwargs)
    else:
        engine = ListensRecordingSimilarity(**kwargs)
    yield from engine.run()
