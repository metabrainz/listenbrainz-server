import re
import uuid
import unittest
import tempfile
from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark.stats import adjust_days
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import create_dataframes
from listenbrainz_spark import schema, utils, config, path, hdfs_connection, stats

from pyspark.sql import Row


class CreateDataframeTestCase(SparkTestCase):
    # path used in between test functions of this class
    listens_path = path.LISTENBRAINZ_DATA_DIRECTORY
    mapping_path = path.MBID_MSID_MAPPING
    mapped_listens_path = path.MAPPED_LISTENS

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        #cls.upload_test_listen_to_HDFS()
        cls.upload_test_mapping_to_hdfs()
        #cls.upload_test_mapped_listens_to_HDFS()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    @classmethod
    def get_test_listen(cls, date):

        test_listen = {
            "artist_mbids": [],
            "artist_msid": "6276299c-57e9-4014-9fdd-ab9ed800f61d",
            "artist_name": "Cake",
            "listened_at": date,
            "recording_msid": "c559b2f8-41ff-4b55-ab3c-0b57d9b85d11",
            "recording_mbid": "1750f8ca-410e-4bdc-bf90-b0146cb5ee35",
            "release_mbid": "",
            "release_msid": "",
            "release_name": "",
            "tags": [],
            "track_name": "Tougher Than It Is",
            "user_name": "vansika",
        }

        return test_listen

    @classmethod
    def upload_test_mapping_to_hdfs(cls):
        tmp_hdfs_path = tempfile.mkdtemp()
        utils.upload_to_HDFS(tmp_hdfs_path, cls.path_to_data_file('msid_mbid_mapping.json'))
        msid_mbid_mapping_df = utils.read_json(tmp_hdfs_path, schema=schema.msid_mbid_mapping_schema)

        utils.save_parquet(msid_mbid_mapping_df, cls.mapping_path)

    @classmethod
    def upload_test_mapped_listens_to_HDFS(cls):
        partial_listen_df = create_dataframes.get_listens_for_training_model_window(cls.date, cls.date, {}, cls.listens_path)
        mapping_df = utils.read_files_from_HDFS(cls.mapping_path)

        mapped_listens = create_dataframes.get_mapped_artist_and_recording_mbids(partial_listen_df, mapping_df)
        utils.save_parquet(mapped_listens, cls.mapped_listens_path)

    @classmethod
    def get_partial_listens_df(cls):
        schema = StructType(
            (
                StructField('artist_msid', StringType(), nullable=True),
                StructField('artist_name', StringType(), nullable=False),
                StructField('listened_at', TimestampType(), nullable=False),
                StructField('recording_msid', StringType(), nullable=True),
                StructField('release_mbid', StringType(), nullable=True),
                StructField('release_msid', StringType(), nullable=True),
                StructField('release_name', StringType(), nullable=True),
                StructField('tags', ArrayType(StringType()), nullable=True),
                StructField('track_name', StringType(), nullable=False),
                StructField('user_name', StringType(), nullable=False)
            )
        )

        tmp_hdfs_path = tempfile.mkdtemp()
        utils.upload_to_HDFS(tmp_hdfs_path, cls.path_to_data_file('msid_mbid_mapping.json'))
        partial_listens_df = utils.read_json(tmp_hdfs_path, schema=schema)
        return partial_listens_df

    def test_get_dates_to_train_data(self):
        date_1 = datetime(2020, 7, 11)
        df = utils.create_dataframe(Row(listened_at=date_1), schema=None)
        df = df.union(utils.create_dataframe(Row(listened_at=adjust_days(date_1, 7)), schema=None))
        utils.save_parquet(df, '{}/2020/7.parquet'.format(self.listens_path))

        date_2 = datetime(2020, 6, 30)
        df = utils.create_dataframe(Row(listened_at=date_2), schema=None)
        df = df.union(utils.create_dataframe(Row(listened_at=adjust_days(date_2, 1)), schema=None))
        utils.save_parquet(df, '{}/2020/6.parquet'.format(self.listens_path))

        train_model_window = 12
        to_date, from_date = create_dataframes.get_dates_to_train_data(train_model_window)
        self.assertEqual(to_date, date_1)
        # shift to the first of the month
        self.assertEqual(from_date, datetime(2020, 6, 1))

        utils.delete_dir(self.listens_path, recursive=True)

    def test_get_listens_for_training_model_window(self):
        metadata = {}
        to_date = datetime(2020, 7, 11)
        df = utils.create_dataframe(self.get_test_listen(to_date), schema.listen_schema)
        df = df.union(utils.create_dataframe(self.get_test_listen(adjust_days(to_date, 7)), schema.listen_schema))
        utils.save_parquet(df, '{}/2020/7.parquet'.format(self.listens_path))

        from_date = datetime(2020, 6, 30)
        df = utils.create_dataframe(self.get_test_listen(from_date), schema.listen_schema)
        df = df.union(utils.create_dataframe(self.get_test_listen(adjust_days(from_date, 1)), schema.listen_schema))
        utils.save_parquet(df, '{}/2020/6.parquet'.format(self.listens_path))

        date = datetime(2020, 5, 30)
        df = utils.create_dataframe(self.get_test_listen(from_date), schema.listen_schema)
        utils.save_parquet(df, '{}/2020/5.parquet'.format(self.listens_path))

        df = create_dataframes.get_listens_for_training_model_window(to_date, from_date, metadata, self.listens_path)
        self.assertEqual(metadata['to_date'], to_date)
        self.assertEqual(metadata['from_date'], from_date)
        df.show()
        self.assertEqual(df.count(), 4)

        cols = [
            "artist_msid",
            "artist_name",
            "listened_at",
            "recording_msid",
            "release_mbid",
            "release_msid",
            "release_name",
            "tags",
            "track_name",
            "user_name",
        ]
        self.assertEqual(sorted(cols), sorted(df.columns))

        utils.delete_dir(self.listens_path, recursive=True)

    def test_save_dataframe(self):
        path_ = '/test_df.parquet'
        df = utils.create_dataframe(Row(column1=1, column2=2), schema=None)
        create_dataframes.save_dataframe(df, path_)

        status = utils.path_exists(path_)
        self.assertTrue(status)

    def test_get_mapped_artist_and_recording_mbids(self):
        partial_listen_df = cls.get_partial_listens_df()
        msid_mbid_mapping_df = utils.read_files_from_HDFS(self.mapping_path)

        mapped_listens_df = create_dataframes.get_mapped_artist_and_recording_mbids(partial_listen_df, msid_mbid_mapping_df)
        self.assertEqual(mapped_listens_df.count(), 1)
        self.assertListEqual(sorted(schema.msid_mbid_mapping_schema.fieldNames()), sorted(mapped_listens_df.columns))
        status = utils.path_exists(mapped_listens_path)
        self.assertTrue(status)

    def test_get_users_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, metadata)
        self.assertEqual(users_df.count(), 1)
        self.assertListEqual(sorted(self.get_users_df().columns), sorted(users_df.columns))
        self.assertEqual(metadata['users_count'], users_df.count())

        status = utils.path_exists(path.USERS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_recordings_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, metadata)
        self.assertEqual(recordings_df.count(), 1)
        self.assertListEqual(sorted(self.get_recordings_df().columns), sorted(recordings_df.columns))
        self.assertEqual(metadata['recordings_count'], 1)

        status = utils.path_exists(path.RECORDINGS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_listens_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        listens_df = create_dataframes.get_listens_df(mapped_listens, metadata)
        self.assertEqual(listens_df.count(), 1)
        self.assertListEqual(['mb_recording_mbid', 'user_name'], listens_df.columns)
        self.assertEqual(metadata['listens_count'], 1)

    def test_get_playcounts_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, {})
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, {})
        listens_df = create_dataframes.get_listens_df(mapped_listens, {})

        playcounts_df = create_dataframes.get_playcounts_df(listens_df, recordings_df, users_df, metadata)
        self.assertEqual(playcounts_df.count(), 1)
        self.assertListEqual(['user_id', 'recording_id', 'count'], playcounts_df.columns)
        self.assertEqual(metadata['playcounts_count'], playcounts_df.count())

        status = utils.path_exists(path.PLAYCOUNTS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_generate_dataframe_id(self):
        metadata = {}
        create_dataframes.generate_dataframe_id(metadata)
        assert re.match('{}-*'.format(config.DATAFRAME_ID_PREFIX), metadata['dataframe_id'])

    def test_save_dataframe_metadata_to_HDFS(self):
        df_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = self.get_dataframe_metadata(df_id)
        create_dataframes.save_dataframe_metadata_to_hdfs(metadata)

        status = utils.path_exists(path.DATAFRAME_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(path.DATAFRAME_METADATA)
        self.assertTrue(sorted(df.columns), sorted(schema.dataframe_metadata_schema.fieldNames()))
