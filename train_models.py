import itertools
import os
import sys
import ujson
import utils

from collections import namedtuple
from math import sqrt
from operator import add
from pyspark.mllib.recommendation import ALS, Rating
from pyspark.sql import Row
from setup import spark, sc

Model = namedtuple('Model', 'model error rank lmbda iteration')


def parse_playcount(row):
    return Rating(row['user_id'], row['recording_id'], row['count'])


def compute_rmse(model, data, n):
    """ Compute RMSE (Root Mean Squared Error).
    """
    predictions = model.predictAll(data.map(lambda x: (x.user, x.product)))
    predictionsAndRatings = predictions.map(lambda x: ((x[0], x[1]), x[2])) \
      .join(data.map(lambda x: ((x[0], x[1]), x[2]))) \
      .values()
    return sqrt(predictionsAndRatings.map(lambda x: (x[0] - x[1]) ** 2).reduce(add) / float(n))


def split_data(directory):
    playcounts_df = utils.load_playcounts_df(directory)
    print(playcounts_df.show())
    training_data, validation_data, test_data = playcounts_df.rdd.map(parse_playcount).randomSplit([4, 1, 1], 45)
    return training_data, validation_data, test_data


def train(training_data, validation_data, num_validation, ranks, lambdas, iterations):
    best_model = None
    alpha = 3.0 # controls baseline confidence growth

    for rank, lmbda, iteration in itertools.product(ranks, lambdas, iterations):
        print('Training model with rank = %.2f, lambda = %.2f, iterations = %d...' % (rank, lmbda, iteration))
        model = ALS.trainImplicit(training_data, rank, iterations=iteration, lambda_=lmbda, alpha=alpha)
        validation_rmse = compute_rmse(model, validation_data, num_validation)
        print("    RMSE (validation) = %f for the model trained with " % validation_rmse + \
              "rank = %d, lambda = %.1f, and numIter = %d." % (rank, lmbda, iteration))
        if best_model is None or validation_rmse < best_model.error:
            best_model = Model(model=model, error=validation_rmse, rank=rank, lmbda=lmbda, iteration=iteration)

    print('Best model has error = %.2f, rank = %.2f, lambda = %.2f, iteration=%d' %
            (best_model.error, best_model.rank, best_model.lmbda, best_model.iteration))
    return best_model


def main(table_dir, output_dir):
    training_data, validation_data, test_data = split_data(table_dir)
    num_training = training_data.count()
    num_validation = validation_data.count()
    num_test = test_data.count()
    print('%d, %d, %d' % (training_data.count(), validation_data.count(), test_data.count()))
    model = train(training_data, validation_data, num_validation, [8, 12], [0.1, 10.0], [10, 20])
    model.model.save(sc, os.path.join(output_dir, 'listenbrainz-recommendation-model'))
    with open(os.path.join(output_dir, 'model-details.json'), 'w') as f:
        print(ujson.dumps({
            'rank': model.rank,
            'lambda': model.lmbda,
            'iteration': model.iteration,
            'error': model.error,
        }), file=f)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python train_model.py [table_dir] [data_dir]")
        sys.exit(0)

    table_dir = sys.argv[1]
    output_dir = sys.argv[2]
    main(table_dir, output_dir)
