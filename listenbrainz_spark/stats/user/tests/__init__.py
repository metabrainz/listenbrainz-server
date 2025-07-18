import json

from listenbrainz_spark.hdfs.utils import delete_dir, upload_to_HDFS
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.postgres.artist import unpersist_artist_country_cache
from listenbrainz_spark.postgres.recording import unpersist_recording_artist_cache
from listenbrainz_spark.postgres.release import unpersist_release_metadata_cache
from listenbrainz_spark.postgres.release_group import unpersist_release_group_metadata_cache
from listenbrainz_spark.tests import SparkNewTestCase


class StatsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StatsTestCase, cls).setUpClass()
        cls.upload_test_listens()
        cls.upload_metadata_cache()

    @classmethod
    def upload_metadata_cache(cls) -> None:
        upload_to_HDFS(
            RELEASE_GROUP_METADATA_CACHE_DATAFRAME,
            cls.path_to_data_file("release_group_metadata_cache.parquet")
        )
        upload_to_HDFS(
            RELEASE_METADATA_CACHE_DATAFRAME,
            cls.path_to_data_file("release_metadata_cache.parquet")
        )
        upload_to_HDFS(
            ARTIST_COUNTRY_CODE_DATAFRAME,
            cls.path_to_data_file("artist_country_code.parquet")
        )
        upload_to_HDFS(
            RECORDING_ARTIST_DATAFRAME,
            cls.path_to_data_file("recording_artist.parquet")
        )

    @classmethod
    def delete_uploaded_metadata_cache(cls) -> None:
        unpersist_release_group_metadata_cache()
        unpersist_release_metadata_cache()
        unpersist_artist_country_cache()
        unpersist_recording_artist_cache()
        delete_dir(RELEASE_GROUP_METADATA_CACHE_DATAFRAME)
        delete_dir(RELEASE_METADATA_CACHE_DATAFRAME)
        delete_dir(ARTIST_COUNTRY_CODE_DATAFRAME)
        delete_dir(RECORDING_ARTIST_DATAFRAME)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.delete_uploaded_listens()
        cls.delete_uploaded_metadata_cache()
        super(StatsTestCase, cls).tearDownClass()

    def assert_user_stats_equal(self, expected_data_file, messages, database_prefix):
        with open(self.path_to_data_file(expected_data_file)) as f:
            expected = json.load(f)

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertTrue(messages[0]["database"].startswith(database_prefix))

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        if "entity" in expected[0]:
            self.assertEqual(messages[1]["entity"], expected[0]["entity"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertTrue(messages[1]["database"].startswith(database_prefix))

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertTrue(messages[2]["database"].startswith(database_prefix))
