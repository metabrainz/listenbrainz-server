from listenbrainz_spark.similarity.artist.listens import ListensArtistSimilarity
from listenbrainz_spark.similarity.artist.mlhd import MlhdArtistSimilarity


def main(mlhd, **kwargs):
    """ Generate similar artists. """
    if mlhd:
        engine = MlhdArtistSimilarity(**kwargs)
    else:
        engine = ListensArtistSimilarity(**kwargs)
    yield from engine.run()
