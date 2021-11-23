from listenbrainz_spark.tests import SparkNewTestCase


class StatsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StatsTestCase, cls).setUpClass()
        cls.upload_test_listens()

    @classmethod
    def tearDownClass(cls) -> None:
        super(StatsTestCase, cls).tearDownClass()
        cls.delete_uploaded_listens()
