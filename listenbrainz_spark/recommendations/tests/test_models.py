import os
import uuid
import unittest

import listenbrainz_spark
from listenbrainz_spark.tests import SparkTestCase, TEST_PLAYCOUNTS_PATH, PLAYCOUNTS_COUNT
from listenbrainz_spark import utils, config, hdfs_connection
from listenbrainz_spark.recommendations import train_models

from pyspark.sql import Row
from pyspark.sql.types import StructType, StructField, IntegerType

class TrainModelsTestCase(SparkTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        super().upload_test_playcounts()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    def test_train(self):
        training_data, validation_data, test_data = super().split_playcounts()
        best_model, model_metadata, best_model_metadata = train_models.train(training_data, validation_data,
            validation_data.count(), self.ranks, self.lambdas, self.iterations)
        self.assertTrue(best_model)
        self.assertEqual(len(model_metadata), 1)
        self.assertEqual(model_metadata[0][0], best_model_metadata['model_id'])
        self.assertEqual(model_metadata[0][1], best_model_metadata['training_time'])
        self.assertEqual(model_metadata[0][2], best_model_metadata['rank'])
        self.assertEqual(model_metadata[0][3], best_model_metadata['lmbda'])
        self.assertEqual(model_metadata[0][4], best_model_metadata['iteration'])
        self.assertEqual(model_metadata[0][5], best_model_metadata['error'])
        self.assertEqual(model_metadata[0][6], best_model_metadata['rmse_time'])

    def test_parse_dataset(self):
        row = Row(user_id=1, recording_id=1, count=1)
        rating_object = train_models.parse_dataset(row)
        self.assertEqual(rating_object.user, 1)
        self.assertEqual(rating_object.product, 1)
        self.assertEqual(rating_object.rating, 1)

    def test_preprocess_data(self):
        test_playcounts_df = utils.read_files_from_HDFS(TEST_PLAYCOUNTS_PATH)
        training_data, validation_data, test_data = train_models.preprocess_data(test_playcounts_df)
        total_playcounts = training_data.count() + validation_data.count() + test_data.count()
        self.assertEqual(total_playcounts, PLAYCOUNTS_COUNT)

    def test_save_model(self):
        training_data, validation_data, test_data = super().split_playcounts()
        best_model, _, best_model_metadata = train_models.train(training_data, validation_data,
            validation_data.count(), self.ranks, self.lambdas, self.iterations)
        model_save_path = os.path.join('/test/model', best_model_metadata['model_id'])
        train_models.save_model(model_save_path, best_model_metadata['model_id'], best_model)
        model_exist = utils.path_exists(model_save_path)
        self.assertTrue(model_exist)
