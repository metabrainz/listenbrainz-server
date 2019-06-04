#!/bin/bash

zip -r listenbrainz_spark.zip listenbrainz_spark/
time ./run.sh /usr/local/spark/bin/spark-submit --master spark://spark-master.spark-network:7077 --num-executors=28 --executor-memory=1g --driver-memory=1g --py-files listenbrainz_spark.zip "$@"

