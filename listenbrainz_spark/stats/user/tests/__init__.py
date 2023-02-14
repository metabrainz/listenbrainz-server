from listenbrainz_spark.hdfs import upload_to_HDFS, delete_dir
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.tests import SparkNewTestCase


class StatsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StatsTestCase, cls).setUpClass()
        cls.upload_test_listens()
        upload_to_HDFS(
            RELEASE_METADATA_CACHE_DATAFRAME,
            cls.path_to_data_file("release_data_cache.parquet")
        )
        upload_to_HDFS(
            ARTIST_COUNTRY_CODE_DATAFRAME,
            cls.path_to_data_file("artist_country_code.parquet")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super(StatsTestCase, cls).tearDownClass()
        cls.delete_uploaded_listens()
        delete_dir(RELEASE_METADATA_CACHE_DATAFRAME)
        delete_dir(ARTIST_COUNTRY_CODE_DATAFRAME)
