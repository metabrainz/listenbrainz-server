import os
import sys
import json
import uuid
import logging
import itertools
from math import sqrt
from time import time
from operator import add
from datetime import datetime
from collections import namedtuple
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.recommendations import utils

from pyspark.sql import Row
from pyspark.sql.utils import AnalysisException
from pyspark.mllib.recommendation import ALS, Rating

Model = namedtuple('Model', 'model error rank lmbda iteration model_id training_time rmse_time')

def parse_dataset(row):
    return Rating(row['user_id'], row['recording_id'], row['count'])

def compute_rmse(model, data, n):
    """ Compute RMSE (Root Mean Squared Error).
    """
    predictions = model.predictAll(data.map(lambda x: (x.user, x.product)))
    predictionsAndRatings = predictions.map(lambda x: ((x[0], x[1]), x[2])) \
      .join(data.map(lambda x: ((x[0], x[1]), x[2]))) \
      .values()
    return sqrt(predictionsAndRatings.map(lambda x: (x[0] - x[1]) ** 2).reduce(add) / float(n))

def preprocess_data(playcounts_df):
    logging.info('Splitting dataframe...')
    training_data, validation_data, test_data = playcounts_df.rdd.map(parse_dataset).randomSplit([4, 1, 1], 45)
    return training_data, validation_data, test_data

def train(training_data, validation_data, num_validation, ranks, lambdas, iterations):
    best_model = None
    best_model_metadata = {}
    model_metadata = []
    alpha = 3.0
    for rank, lmbda, iteration in itertools.product(ranks, lambdas, iterations):
        t0 = time()
        model = ALS.trainImplicit(training_data, rank, iterations=iteration, lambda_=lmbda, alpha=alpha)
        mt = '{:.2f}'.format((time() - t0) / 60)
        model_id = 'listenbrainz-recommendation-model-{}'.format(uuid.uuid4())
        t0 = time()
        validation_rmse = compute_rmse(model, validation_data, num_validation)
        vt = '{:.2f}'.format((time() - t0) / 60)
        model_metadata.append((model_id, mt, rank, '{:.1f}'.format(lmbda), iteration, "%.2f" % (validation_rmse), vt))
        if best_model is None or validation_rmse < best_model.error:
            best_model = Model(model=model, error=validation_rmse, rank=rank, lmbda=lmbda, iteration=iteration,             model_id=model_id, training_time=mt, rmse_time=vt)
    best_model_metadata = {'error': '{:.2f}'.format(best_model.error), 'rank': best_model.rank, 'lmbda':
            best_model.lmbda, 'iteration': best_model.iteration, 'model_id': best_model.model_id, 'training_time': best_model.training_time, 'rmse_time': best_model.rmse_time}
    return best_model, model_metadata, best_model_metadata

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Train_Models')
    except AttributeError as err:
        logging.error('Cannot initialize Spark Session: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred while initializing Spark session: {} \n {}. Aborting...'.format(type(err)          .__name__,str(err)), exc_info=True)
        sys.exit(-1)

    try:
        path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'dataframes',                             'playcounts_df.parquet')
        playcounts_df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + path)
    except AnalysisException as err:
        logging.error('Cannot read parquet file from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while fetching parquet: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err)), exc_info=True)
        sys.exit(-1)
    time_info = {}
    time_info['load_playcounts'] = '{:.2f}'.format((time() - ti) / 60)

    t0 = time()
    training_data, validation_data, test_data = preprocess_data(playcounts_df)
    time_info['preprocessing'] = '{:.2f}'.format((time() - t0) / 60)

    # Rdds that are used in model training iterative process are cached to improve performance.
    # Caching large files may cause Out of Memory exception.
    training_data.persist()
    validation_data.persist()
    num_training = training_data.count()
    num_validation = validation_data.count()
    num_test = test_data.count()
    logging.info('Training models...')

    try:
        t0 = time()
        model, model_metadata, best_model_metadata = train(training_data, validation_data, num_validation,                  config.RANKS, config.LAMBDAS, config.ITERATIONS)
        models_training_time = '{:.2f}'.format((time() - t0) / 3600)
    except Py4JJavaError as err:
        logging.error('Unable to train models: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while training models: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err),exc_info=True))
        sys.exit(-1)

    training_data.unpersist()
    validation_data.unpersist()

    logging.info('Saving model...')
    try:
        t0 = time()
        path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'best-model', '{}'.format                 (best_model_metadata['model_id']))
        model.model.save(listenbrainz_spark.context, config.HDFS_CLUSTER_URI + path)
        time_info['save_model'] = '{:.2f}'.format((time() - t0) / 60)
    except Py4JJavaError as err:
        logging.error("Unable to save model: {} \n {}. Aborting...".format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while saving model: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err),exc_info=True))
        sys.exit(-1)

    date = datetime.utcnow().strftime('%Y-%m-%d')
    model_html = 'Model-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'time' : time_info,
        'num_training' : '{:,}'.format(num_training),
        'num_validation' : '{:,}'.format(num_validation),
        'num_test' : '{:,}'.format(num_test),
        'models' : model_metadata,
        'best_model' : best_model_metadata,
        'models_training_time' : models_training_time,
        'total_time' : '{:.2f}'.format((time() - ti) / 3600)
    }

    utils.save_html(model_html, context, 'model.html')
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommendation-metadata.json')
    with open(path, 'r') as f:
        recommendation_metadata = json.load(f)
        recommendation_metadata['best_model_id'] = best_model_metadata['model_id']

    with open(path, 'w') as f:
        json.dump(recommendation_metadata,f)
