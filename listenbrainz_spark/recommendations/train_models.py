import itertools
import os
import sys
import json
import time
import listenbrainz_spark
import logging

from collections import namedtuple
from math import sqrt
from operator import add
from pyspark.mllib.recommendation import ALS, Rating
from pyspark.sql import Row
from datetime import datetime
from listenbrainz_spark import config
from listenbrainz_spark.recommendations import utils
from time import sleep

Model = namedtuple('Model', 'model error rank lmbda iteration')

def parse_dataset(row):
    return Rating(row['user_id'], row['recording_id'], row['count'])

def compute_rmse(model, data, n):
    """ Compute RMSE (Root Mean Squared Error).
    """
    predictions = model.predictAll(data.map(lambda x: (x.user, x.product)))
    predictions.collect()
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
    model_info = {}
    training_metadata = []
    alpha = 3.0 
    t0 = time.time()
    for rank, lmbda, iteration in itertools.product(ranks, lambdas, iterations):
        model = ALS.trainImplicit(training_data, rank, iterations=iteration, lambda_=lmbda, alpha=alpha)
        validation_rmse = compute_rmse(model, validation_data, num_validation)
        training_metadata.append((rank, "%.1f" % (lmbda), iteration, "%.2f" % (validation_rmse)))
        if best_model is None or validation_rmse < best_model.error:
            best_model = Model(model=model, error=validation_rmse, rank=rank, lmbda=lmbda, iteration=iteration)
    model_info["training_metadata"] = training_metadata
    model_info["best_model"] = {'error': "%.2f" % (best_model.error), 'rank': best_model.rank, 'lmbda': best_model.lmbda, 'iteration': best_model.iteration}
    t = "%.2f" % (time.time() - t0)
    return best_model, model_info, t

def main(df, lb_dump_time_window):
    t0 = time.time()
    training_data, validation_data, test_data = preprocess_data(df)
    t = "%.2f" % (time.time() - t0)
    print("Dataframe split in: %ss" % (t))
    num_training = training_data.count()
    num_validation = validation_data.count()
    num_test = test_data.count()
    print("Training model...")
    model, model_info, t = train(training_data, validation_data, num_validation, [8, 12], [0.1, 10.0], [10, 20])

    print("Saving model...")
    date = datetime.utcnow().strftime("%Y-%m-%d")
    for attempt in range(config.MAX_RETRIES):
        try:
            path = os.path.join('/', 'data', 'listenbrainz','listenbrainz-recommendation-mode-{}'.format(date))
            model.model.save(listenbrainz_spark.context, config.HDFS_CLUSTER_URI + path)
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to save model: %s.Retrying in %ss" % (type(err).__name__, config.TIME_BEFORE_RETRIES))
    outputfile = 'Model-Info-%s.html' % (date)
    context = {
        'total_listens' : num_training+num_validation+num_test,
        'model' : model_info,
        'time' : t,
        'lb_dump_time_window' : lb_dump_time_window,
    }
    utils.save_html(outputfile, context, 'model.html')



    
