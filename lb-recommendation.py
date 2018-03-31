#!/usr/bin/env python3

# I've been working from this page:
# https://github.com/dennyglee/databricks/blob/master/notebooks/Users/denny%40databricks.com/content/Movie%20Recommendations%20with%20MLlib.py

import sys
import ujson
import itertools
from math import sqrt
from operator import add
from os.path import join, isfile, dirname

from pyspark import SparkConf, SparkContext
from pyspark.mllib.recommendation import ALS, Rating

def parse_recording(line):
    """
    Parses a recording record format recording_id, track_name
    """
    js = ujson.loads(line)
    return (int(js['recording_id']), js['track_name'])

def parse_playcount(line):
    js = ujson.loads(line.strip())
    return int(js['recording_id']) % 10, Rating(int(js['user_id']), 
                                                int(js['recording_id']),
                                                int(js['play_count'])) 

def load_playcounts(playcount_file):
    """
    Load playcount from file.
    """
    if not isfile(playcount_file):
        print("File %s does not exist." % playcount_file)
        sys.exit(1)

    playcounts = []
    with open(playcount_file, 'r') as f:
        while True:
            line = f.readline()
            if not line:
                break

            playcounts.append(parse_playcount(line))

    if not playcounts:
        print("No playcounts provided.")
        sys.exit(1)
    else:
        return playcounts

def compute_rmse(model, data, n):
    """
    Compute RMSE (Root Mean Squared Error).
    """
    predictions = model.predictAll(data.map(lambda x: (x[0], x[1])))
    predictionsAndRatings = predictions.map(lambda x: ((x[0], x[1]), x[2])) \
      .join(data.map(lambda x: ((x[0], x[1]), x[2]))) \
      .values()
    return sqrt(predictionsAndRatings.map(lambda x: (x[0] - x[1]) ** 2).reduce(add) / float(n))

if __name__ == "__main__":
    print(sys.argv)
    if (len(sys.argv) != 4):
        print("Usage: /path/to/spark/bin/spark-submit --driver-memory 1g " + \
          "lb-recommendation.py playcount_file id_file user_rating_file output_file")
        sys.exit(1)

    # set up environment
    conf = SparkConf() \
      .setAppName("LB recommender") \
      .set("spark.executor.memory", "1g")
    sc = SparkContext(conf=conf)

    # load personal playcounts
    user_playcounts = sc.textFile(sys.argv[3]).map(parse_playcount)
    
    # playcounts is an RDD of (last digit of timestamp, (user_name, recording_id, play_count))
    playcounts = sc.textFile(sys.argv[1]).map(parse_playcount)

    # movies is an RDD of (movieId, movieTitle)
    recordings = sc.textFile(sys.argv[2]).map(parse_recording)

    num_playcounts = playcounts.count()
    num_users = playcounts.values().map(lambda r: r[0]).distinct().count()
    num_recordings = playcounts.values().map(lambda r: r[1]).distinct().count()

    print("==== Got %d playcounts from %d users on %d recordings." % (num_playcounts, num_users, num_recordings))

    # split playcounts into train (60%), validation (20%), and test (20%) based on the 
    # last digit of the timestamp, add user_playcounts to train, and cache them

    # training, validation, test are all RDDs of (userId, movieId, rating)

    training, test, validation = playcounts.map(lambda x: x[1]).randomSplit([4, 1, 1], 45)
    numTraining = training.count()
    numValidation = validation.count()
    num_test = test.count()

    print("=== Training: %d, validation: %d, test: %d" % (numTraining, numValidation, num_test))

    # train models and evaluate them on the validation set

    ranks = [8, 12]
    lambdas = [0.1, 10.0]
    numIters = [10, 20]
    bestModel = None
    bestValidationRmse = float("inf")
    bestRank = 0
    bestLambda = -1.0
    bestNumIter = -1

    for rank, lmbda, numIter in itertools.product(ranks, lambdas, numIters):
        model = ALS.train(training, rank, numIter, lmbda)
        validationRmse = compute_rmse(model, validation, numValidation)
        print("==== RMSE (validation) = %f for the model trained with " % validationRmse + \
              "rank = %d, lambda = %.1f, and numIter = %d." % (rank, lmbda, numIter))
        if (validationRmse < bestValidationRmse):
            bestModel = model
            bestValidationRmse = validationRmse
            bestRank = rank
            bestLambda = lmbda
            bestNumIter = numIter

    ###### NOT TESTED/DEBUGGED BELOW THIS
    test_rmse = compute_rmse(bestModel, test, num_test)

    # evaluate the best model on the test set
    print("The best model was trained with rank = %d and lambda = %.1f, " % (bestRank, bestLambda) \
      + "and numIter = %d, and its RMSE on the test set is %f." % (bestNumIter, test_rmse))

    # compare the best model with a naive baseline that always returns the mean rating
    mean_rating = training.union(validation).map(lambda x: x[2]).mean()
    baseline_rmse = sqrt(test.map(lambda x: (mean_rating - x[2]) ** 2).reduce(add) / num_test)
    improvement = (baseline_rmse - test_rmse) / baseline_rmse * 100
    print("The best model improves the baseline by %.2f" % (improvement) + "%.")


    # make personalized recommendations
    print('Doing recommendations now...')
    user_recording_ids = user_playcounts.values().map(lambda x: x[1])
    print("Number of user recordings: %d" % user_recording_ids.count())
    all_recording_ids = playcounts.values().map(lambda x: x[1]).distinct()
    print("Number of recordings: %d" % all_recording_ids.count())
    candidates = all_recording_ids.subtract(user_recording_ids)
    print("Number of candidates: %d" % candidates.count())
    current_user_id = user_playcounts.values().first()[0]
    print('user id = %d' % current_user_id)
    predictions = bestModel.predictAll(candidates.map(lambda x: (current_user_id, x))).collect()
    recommendations = sorted(predictions, key=lambda x: x[2], reverse=True)[:50]

    print("recordings recommended for you:")
    for i in range(len(recommendations)):
        print("%2d: %s " % (i + 1, recordings.lookup(recommendations[i][1])))


    # clean up
    sc.stop()
