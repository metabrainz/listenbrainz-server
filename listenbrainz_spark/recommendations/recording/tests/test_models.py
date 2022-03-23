import re
from unittest.mock import patch, Mock, MagicMock

from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
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

    def test_parse_dataset(self):
        row = Row(spark_user_id=1, recording_id=2, count=3)
        rating_object = train_models.parse_dataset(row)
        self.assertEqual(rating_object.user, 1)
        self.assertEqual(rating_object.product, 2)
        self.assertEqual(rating_object.rating, 3)

    @patch('listenbrainz_spark.recommendations.recording.train_models.sqrt')
    @patch('listenbrainz_spark.recommendations.recording.train_models.RDD')
    @patch('listenbrainz_spark.recommendations.recording.train_models.add')
    def test_compute_rmse(self, mock_add,  mock_rdd, mock_sqrt):
        n = 1
        model_id = "281c4177-f33a-441d-b15d-910acaf18b07"
        mock_model = MagicMock()
        _ = train_models.compute_rmse(mock_model, mock_rdd, n, model_id)

        mock_predict_all = mock_model.predictAll
        mock_map = mock_rdd.map()
        mock_predict_all.assert_called_once_with(mock_map)

        mock_predictions = mock_predict_all.return_value.map
        mock_predictions.assert_called_once()

        mock_join = mock_predictions.return_value.join
        mock_join.assert_called_once_with(mock_map)

        mock_values = mock_join.return_value.values
        mock_values.assert_called_once()

        mock_reduce = mock_values.return_value.map.return_value.reduce
        mock_reduce.assert_called_once_with(mock_add)
        # test division operator
        mock_sqrt.assert_called_once_with(mock_reduce.return_value.__truediv__())

    def test_preprocess_data(self):
        test_playcounts_df = utils.read_files_from_HDFS(TEST_PLAYCOUNTS_PATH)
        training_data, validation_data, test_data = train_models.preprocess_data(test_playcounts_df)
        total_playcounts = training_data.count() + validation_data.count() + test_data.count()
        self.assertEqual(total_playcounts, PLAYCOUNTS_COUNT)

    def test_generate_model_id(self):
        model_id = train_models.generate_model_id()
        assert re.match('{}-*'.format(config.MODEL_ID_PREFIX), model_id)

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

        df_metadata = df_1.union(df_2)

        expected_dataframe_id = train_models.get_latest_dataframe_id(df_metadata)
        self.assertEqual(expected_dataframe_id, df_id_2)

    def test_get_best_model_metadata(self):
        mock_model = MagicMock()
        best_model = train_models.Model(
            model=mock_model,
            validation_rmse=3.9,
            rank=4,
            lmbda=2.1,
            iteration=1,
            model_id="xxx",
            training_time="3.1",
            rmse_time="2.1",
            alpha=3.0,
        )

        metadata = train_models.get_best_model_metadata(best_model)
        self.assertEqual(best_model.validation_rmse, metadata['validation_rmse'])
        self.assertEqual(best_model.rank, metadata['rank'])
        self.assertEqual(best_model.lmbda, metadata['lmbda'])
        self.assertEqual(best_model.iteration, metadata['iteration'])
        self.assertEqual(best_model.model_id, metadata['model_id'])
        self.assertEqual(best_model.training_time, metadata['training_time'])
        self.assertEqual(best_model.rmse_time, metadata['rmse_time'])
        self.assertEqual(best_model.alpha, metadata['alpha'])

    @patch('listenbrainz_spark.recommendations.recording.train_models.RDD')
    @patch('listenbrainz_spark.recommendations.recording.train_models.ALS')
    def test_train(self, mock_als, mock_rdd):
        rank = 2
        iteration = 2
        lmbda = 2.0
        alpha = 1.0
        model_id = 'xxxxxxx'
        _ = train_models.train(mock_rdd, rank, iteration, lmbda, alpha, model_id)

        mock_als.trainImplicit.assert_called_once_with(mock_rdd, rank, iterations=iteration, lambda_=lmbda, alpha=alpha)

    @patch('listenbrainz_spark.recommendations.recording.train_models.compute_rmse')
    @patch('listenbrainz_spark.recommendations.recording.train_models.train')
    @patch('listenbrainz_spark.recommendations.recording.train_models.generate_model_id')
    def test_get_best_model(self, mock_id, mock_train, mock_rmse):
        mock_rdd_training = Mock()
        mock_rdd_validation = Mock()
        num_validation = 4
        ranks = [3]
        lambdas = [4.8]
        iterations = [2]
        alphas = [3.0]
        mock_rmse.return_value = 6.999
        best_model, model_metadata = train_models.get_best_model(mock_rdd_training, mock_rdd_validation, num_validation,
                                                                 ranks, lambdas, iterations, alphas)
        mock_id.assert_called_once()
        mock_train.assert_called_once_with(mock_rdd_training, ranks[0], iterations[0], lambdas[0],
                                           alphas[0], mock_id.return_value)
        mock_rmse.assert_called_once_with(mock_train.return_value, mock_rdd_validation, num_validation, mock_id.return_value)

    def test_delete_model(self):
        df = utils.create_dataframe(Row(col1=1, col2=1), None)
        utils.save_parquet(df, path.RECOMMENDATION_RECORDING_DATA_DIR)
        train_models.delete_model()

        dir_exists = utils.path_exists(path.RECOMMENDATION_RECORDING_DATA_DIR)
        self.assertFalse(dir_exists)

    def test_save_model_metadata_to_hdfs(self):
        model_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = self.get_model_metadata(model_id)

        train_models.save_model_metadata_to_hdfs(metadata)

        status = utils.path_exists(path.RECOMMENDATION_RECORDING_MODEL_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_MODEL_METADATA)
        self.assertTrue(sorted(df.columns), sorted(schema.model_metadata_schema.fieldNames()))

    @patch('listenbrainz_spark.recommendations.recording.train_models.listenbrainz_spark')
    @patch('listenbrainz_spark.recommendations.recording.train_models.get_model_path')
    @patch('listenbrainz_spark.recommendations.recording.train_models.delete_model')
    def test_save_model(self, mock_del, mock_path, mock_context):
        model_id = 'xxxxxx'
        mock_model = MagicMock()
        train_models.save_model(model_id, mock_model)

        mock_del.assert_called_once()
        mock_path.assert_called_once_with(model_id)
        mock_model.save.assert_called_once_with(mock_context.context, mock_path.return_value)
