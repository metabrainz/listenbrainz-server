#!/bin/bash

source config.sh

zip -r listenbrainz_spark.zip listenbrainz_spark/
time ./run.sh /usr/local/spark/bin/spark-submit \
	--packages org.apache.spark:spark-avro_2.11:2.4.1 \
	--master $SPARK_URI \
	--num-executors=$EXECUTOR_COUNT \
	--executor-memory=$EXECUTOR_MEMORY \
	--driver-memory=$DRIVER_MEMORY \
	--py-files listenbrainz_spark.zip \
	"$@"
