import unittest
import uuid
import listenbrainz_spark

from listenbrainz_spark import hdfs_connection, utils, config

class SparkTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        listenbrainz_spark.init_test_session('spark-test-run-{}'.format(str(uuid.uuid4())))
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)

    @classmethod
    def tearDownClass(cls):
        listenbrainz_spark.context.stop()
