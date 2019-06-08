#!/bin/bash

zip -r listenbrainz_spark.zip listenbrainz_spark/
time ./run.sh /usr/local/spark/bin/spark-submit \
	--packages org.apache.spark:spark-avro_2.11:2.4.1 \
	--master spark://spark-master.spark-network:7077 \
	--num-executors=7 \
	--executor-memory=3g \
	--driver-memory=6g \
	--py-files listenbrainz_spark.zip \
	"$@"

