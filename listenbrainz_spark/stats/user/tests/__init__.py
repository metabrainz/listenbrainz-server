from listenbrainz_spark.hdfs.utils import delete_dir, upload_to_HDFS
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME, ARTIST_CREDIT_MBID_DATAFRAME, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.tests import SparkNewTestCase


class StatsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StatsTestCase, cls).setUpClass()
        cls.upload_test_listens()
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
            ARTIST_CREDIT_MBID_DATAFRAME,
            cls.path_to_data_file("artist_credit_mbid.parquet")
        )
        upload_to_HDFS(
            RECORDING_ARTIST_DATAFRAME,
            cls.path_to_data_file("recording_artist.parquet")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super(StatsTestCase, cls).tearDownClass()
        cls.delete_uploaded_listens()
        delete_dir(RELEASE_GROUP_METADATA_CACHE_DATAFRAME)
        delete_dir(RELEASE_METADATA_CACHE_DATAFRAME)
        delete_dir(ARTIST_COUNTRY_CODE_DATAFRAME)
        delete_dir(ARTIST_CREDIT_MBID_DATAFRAME)
        delete_dir(RECORDING_ARTIST_DATAFRAME)
