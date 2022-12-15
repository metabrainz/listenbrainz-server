from unittest import mock
from unittest.mock import patch, MagicMock

from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
from listenbrainz_spark.recommendations.recording.train_models import Model, NUM_FOLDS
from listenbrainz_spark.hdfs.utils import delete_dir
from listenbrainz_spark.hdfs.utils import path_exists
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
        training_data, test_data = train_models.preprocess_data(test_playcounts_df, {})
        total_playcounts = training_data.count() + test_data.count()
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

    @patch('listenbrainz_spark.recommendations.recording.train_models.get_models')
    @patch('listenbrainz_spark.recommendations.recording.train_models.RegressionEvaluator')
    @patch('listenbrainz_spark.recommendations.recording.train_models.CrossValidator')
    @patch('listenbrainz_spark.recommendations.recording.train_models.ParamGridBuilder')
    @patch('listenbrainz_spark.recommendations.recording.train_models.ALS')
    def test_get_best_model(self, mock_als_cls, mock_params, mock_tvs, mock_evaluator, mock_get_models):
        mock_test = MagicMock()
        mock_training = MagicMock()
        mock_get_models.return_value = MagicMock(), MagicMock()

        ranks = [3]
        lambdas = [4.8]
        iterations = [2]
        alphas = [3.0]

        _, __ = train_models.train_models(mock_training, mock_test, True, ranks, lambdas, iterations, alphas, {})
        mock_als_cls.assert_called_once_with(
            userCol="spark_user_id", itemCol="recording_id", ratingCol="transformed_listencount",
            implicitPrefs=True, coldStartStrategy="drop"
        )
        mock_params.assert_called_once()
        mock_evaluator.assert_called_once_with(
            metricName="rmse",
            labelCol="transformed_listencount",
            predictionCol="prediction"
        )
        mock_tvs.assert_called_once_with(
            estimator=mock_als_cls.return_value,
            estimatorParamMaps=mock.ANY,
            evaluator=mock_evaluator.return_value,
            numFolds=NUM_FOLDS,
            collectSubModels=True,
            parallelism=3
        )
        mock_tvs.return_value.fit.assert_called_once_with(mock_training)

    def test_delete_model(self):
        df = utils.create_dataframe(Row(col1=1, col2=1), None)
        utils.save_parquet(df, path.RECOMMENDATION_RECORDING_DATA_DIR)
        train_models.delete_model()

        dir_exists = path_exists(path.RECOMMENDATION_RECORDING_DATA_DIR)
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
            model=MagicMock()
        )

        train_models.save_model_metadata_to_hdfs(metadata, {
            "model_html_file": f"{model_id}.html",
            "test_rmse": 4.5
        })

        status = path_exists(path.RECOMMENDATION_RECORDING_MODEL_METADATA)
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
            model=MagicMock()
        )
        train_models.save_model(mock_model, {
            "model_html_file": f"{mock_model.model_id}.html",
            "test_rmse": 4.5
        })

        mock_del.assert_called_once()
        mock_path.assert_called_once_with(mock_model.model_id)
        mock_model.model.save.assert_called_once_with(mock_path.return_value)
