import unittest
import uuid
import listenbrainz_spark

class SparkTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        listenbrainz_spark.init_test_session('spark-test-run-{}'.format(str(uuid.uuid4())))

    @classmethod
    def tearDownClass(cls):
        listenbrainz_spark.context.stop()
