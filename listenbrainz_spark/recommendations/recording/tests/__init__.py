from listenbrainz_spark.tests import SparkNewTestCase


class RecommendationsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(RecommendationsTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super(RecommendationsTestCase, cls).tearDownClass()

    @classmethod
    def get_dataframe_metadata(cls, df_id):
        return {
            'dataframe_id': df_id,
            'from_date': cls.begin_date,
            'listens_count': 30,
            'playcounts_count': 20,
            'recordings_count': 24,
            'to_date': cls.end_date,
            'users_count': 2,
        }
