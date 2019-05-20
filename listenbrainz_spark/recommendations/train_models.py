import itertools
import os
import sys
import json
import time
import listenbrainz_spark
import logging
import uuid

from collections import namedtuple
from math import sqrt
from operator import add
from pyspark.mllib.recommendation import ALS, Rating
from pyspark.sql import Row
from datetime import datetime
from listenbrainz_spark import config
from listenbrainz_spark.recommendations import utils
from time import sleep

Model = namedtuple('Model', 'model error rank lmbda iteration model_id time')

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
    print("\nSplitting dataframe...")
    training_data, validation_data, test_data = playcounts_df.rdd.map(parse_dataset).randomSplit([4, 1, 1], 45)
    return training_data, validation_data, test_data

def train(training_data, validation_data, num_validation, ranks, lambdas, iterations):
    best_model = None
    best_model_metadata = {}
    model_metadata = []
    alpha = 3.0 
    for rank, lmbda, iteration in itertools.product(ranks, lambdas, iterations):
        t0 = time.time()
        model = ALS.trainImplicit(training_data, rank, iterations=iteration, lambda_=lmbda, alpha=alpha)
        mt = "%.2f" % ((time.time() - t0) / 60)
        model_id = 'listenbrainz-recommendation-model-{}'.format(uuid.uuid4())
        t0  =time.time()
        validation_rmse = compute_rmse(model, validation_data, num_validation)
        vt = "%.2f" % ((time.time() - t0) / 60)
        model_metadata.append((model_id, mt, rank, "%.1f" % (lmbda), iteration, "%.2f" % (validation_rmse), vt))
        if best_model is None or validation_rmse < best_model.error:
            best_model = Model(model=model, error=validation_rmse, rank=rank, lmbda=lmbda, iteration=iteration, model_id=model_id, time=mt)
    best_model_metadata = {'error': "%.2f" % (best_model.error), 'rank': best_model.rank, 'lmbda': best_model.lmbda, 
                            'iteration': best_model.iteration, 'model_id': best_model.model_id, 'time' : best_model.time}
    return best_model, model_metadata, best_model_metadata

def main(df):
    time_info = {}
    t0 = time.time()
    training_data, validation_data, test_data = preprocess_data(df)
    t = "%.2f" % ((time.time() - t0) / 60)
    time_info['preprocessing'] = t

    num_training = training_data.count()
    num_validation = validation_data.count()
    num_test = test_data.count()
    print("Training model...")

    t0 = time.time()
    model, model_metadata, best_model_metadata = train(training_data, validation_data, num_validation, [8, 12], [0.1, 10.0], [10, 20])
    t = "%.2f" % ((time.time() - t0) / 3600)
    models_training_time = t

    print("Saving model...")
    date = datetime.utcnow().strftime("%Y-%m-%d")
    for attempt in range(config.MAX_RETRIES):
        try:
            t0 = time.time()
            path = os.path.join('/', 'data', 'listenbrainz', '{}'.format(best_model_metadata['model_id']))
            model.model.save(listenbrainz_spark.context, config.HDFS_CLUSTER_URI + path)
            t = "%.2f" % ((time.time() - t0) / 60)
            time_info['save_model'] = t
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to save model: %s.Retrying in %ss" % (str(err), config.TIME_BEFORE_RETRIES))
    
    outputfile = 'Model-Info-%s.html' % (date)
    context = {
        'time' : time_info,
        'num_training' : "{:,}".format(num_training),
        'num_validation' : "{:,}".format(num_validation),
        'num_test' : "{:,}".format(num_test),
        'models' : model_metadata,
        'best_model' : best_model_metadata,
        'models_training_time' : models_training_time,
        'link' : 'Recommendations-%s.html' % (date)
    }
    utils.save_html(outputfile, context, 'model.html')
    return best_model_metadata['model_id']
