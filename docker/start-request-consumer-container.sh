#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

source config.sh

CONTAINER_NAME="spark-request-consumer"

docker pull metabrainz/listenbrainz-spark-request-consumer:latest

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/
docker run \
    -d \
    -v `pwd`:/rec \
    --network spark-network \
    --name $CONTAINER_NAME \
    metabrainz/listenbrainz-spark-request-consumer:latest \
    /usr/local/spark/bin/spark-submit \
        --packages org.apache.spark:spark-avro_2.11:2.4.1 \
        --master $SPARK_URI \
        --conf "spark.scheduler.listenerbus.eventqueue.capacity"=$LISTENERBUS_CAPACITY \
        --conf "spark.cores.max"=$MAX_CORES \
        --conf "spark.executor.cores"=$EXECUTOR_CORES \
        --conf "spark.executor.memory"=$EXECUTOR_MEMORY \
        --conf "spark.driver.memory"=$DRIVER_MEMORY \
        --py-files listenbrainz_spark_request_consumer.zip \
	manage.py request_consumer
