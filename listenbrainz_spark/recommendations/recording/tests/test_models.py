import re
from unittest.mock import patch, Mock, MagicMock

from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
from listenbrainz_spark.recommendations.recording.train_models import Model
from listenbrainz_spark.tests import TEST_PLAYCOUNTS_PATH, PLAYCOUNTS_COUNT
from listenbrainz_spark import utils, config, path, schema
from listenbrainz_spark.recommendations.recording import train_models

from pyspark.sql import Row


class TrainModelsTestCase(RecommendationsTestCase):

    @classmethod
    def setUpClass(cls):
        super(TrainModelsTestCase, cls).setUpClass()
        super(TrainModelsTestCase, cls).upload_test_playcounts()

    @classmethod
    def tearDownClass(cls):
        super(TrainModelsTestCase, cls).tearDownClass()
        super(TrainModelsTestCase, cls).delete_dir()

    def test_preprocess_data(self):
        test_playcounts_df = utils.read_files_from_HDFS(TEST_PLAYCOUNTS_PATH)
        training_data, validation_data, test_data = train_models.preprocess_data(test_playcounts_df, {})
        total_playcounts = training_data.count() + validation_data.count() + test_data.count()
        self.assertEqual(total_playcounts, PLAYCOUNTS_COUNT)

    def test_get_model_path(self):
        model_id = "a36d6fc9-49d0-4789-a7dd-a2b72369ca45"
        actual_path = train_models.get_model_path(model_id)
        expected_path = config.HDFS_CLUSTER_URI + path.RECOMMENDATION_RECORDING_DATA_DIR + '/' + model_id
        self.assertEqual(actual_path, expected_path)

    def test_get_latest_dataframe_id(self):
        df_id_1 = "a36d6fc9-49d0-4789-a7dd-a2b72369ca45"
        df_metadata_dict_1 = self.get_dataframe_metadata(df_id_1)
        df_1 = utils.create_dataframe(schema.convert_dataframe_metadata_to_row(df_metadata_dict_1),
                                      schema.dataframe_metadata_schema)

        df_id_2 = "bbbd6fc9-49d0-4789-a7dd-a2b72369ca45"
        df_metadata_dict_2 = self.get_dataframe_metadata(df_id_2)
        df_2 = utils.create_dataframe(schema.convert_dataframe_metadata_to_row(df_metadata_dict_2),
                                      schema.dataframe_metadata_schema)

        df_1.union(df_2).write.parquet(path.RECOMMENDATION_RECORDING_DATAFRAME_METADATA)

        expected_dataframe_id = train_models.get_latest_dataframe_id()
        self.assertEqual(expected_dataframe_id, df_id_2)

    @patch('listenbrainz_spark.recommendations.recording.train_models.ALS')
    def test_get_best_model(self, mock_als_cls):
        mock_evaluator = MagicMock()
        mock_rdd_training = Mock()
        mock_rdd_validation = Mock()

        mock_als_model = MagicMock()
        mock_als = MagicMock()
        mock_als.fit.return_value = mock_als_model
        mock_als_cls.return_value = mock_als

        ranks = [3]
        lambdas = [4.8]
        iterations = [2]
        alphas = [3.0]

        _, __ = train_models.train_models(mock_rdd_training, mock_rdd_validation, mock_evaluator,
                                          ranks, lambdas, iterations, alphas, {})
        mock_als_cls.assert_called_once_with(
            userCol='spark_user_id', itemCol='recording_id', ratingCol='transformed_listencount',
            rank=ranks[0], maxIter=iterations[0], regParam=lambdas[0], alpha=alphas[0],
            implicitPrefs=True, coldStartStrategy="drop"
        )
        mock_als.fit.assert_called_once_with(mock_rdd_training)
        mock_als_model.transform.assert_called_once_with(mock_rdd_validation)
        mock_evaluator.evaluate.assert_called_once_with(mock_als_model.transform.return_value)

    def test_delete_model(self):
        df = utils.create_dataframe(Row(col1=1, col2=1), None)
        utils.save_parquet(df, path.RECOMMENDATION_RECORDING_DATA_DIR)
        train_models.delete_model()

        dir_exists = utils.path_exists(path.RECOMMENDATION_RECORDING_DATA_DIR)
        self.assertFalse(dir_exists)

    def test_save_model_metadata_to_hdfs(self):
        model_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = Model(
            model_id='3acb406f-c716-45f8-a8bd-96ca3939c2e5',
            alpha=3.0,
            lmbda=2.0,
            iteration=2,
            rank=4,
            validation_rmse=4.5,
            training_time=3.0,
            rmse_time=2.1,
            model=MagicMock()
        )

        train_models.save_model_metadata_to_hdfs(metadata, {
            "model_html_file": f"{model_id}.html",
            "test_rmse": 4.5
        })

        status = utils.path_exists(path.RECOMMENDATION_RECORDING_MODEL_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_MODEL_METADATA)
        self.assertTrue(sorted(df.columns), sorted(schema.model_metadata_schema.fieldNames()))

    @patch('listenbrainz_spark.recommendations.recording.train_models.get_model_path')
    @patch('listenbrainz_spark.recommendations.recording.train_models.delete_model')
    def test_save_model(self, mock_del, mock_path):
        mock_model = Model(
            model_id='xxxxx',
            alpha=3.0,
            lmbda=2.0,
            iteration=2,
            rank=4,
            validation_rmse=4.5,
            training_time=3.0,
            rmse_time=2.1,
            model=MagicMock()
        )
        train_models.save_model(mock_model, {
            "model_html_file": f"{mock_model.model_id}.html",
            "test_rmse": 4.5
        })

        mock_del.assert_called_once()
        mock_path.assert_called_once_with(mock_model.model_id)
        mock_model.model.save.assert_called_once_with(mock_path.return_value)
