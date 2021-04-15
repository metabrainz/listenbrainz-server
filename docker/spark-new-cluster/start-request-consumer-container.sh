#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../../"

source spark_config.sh

CONTAINER_NAME="spark-request-consumer"

docker pull metabrainz/listenbrainz-spark-new-cluster:latest

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/
docker run \
    -d \
    -v /spark:/spark \
    -v /hadoop:/hadoop \
    -v /usr/lib/jvm/adoptopenjdk-11-hotspot-amd64:/usr/lib/jvm/adoptopenjdk-11-hotspot-amd64 \
    -v `pwd`:/rec \
    --network host \
    --name $CONTAINER_NAME \
    metabrainz/listenbrainz-spark-new-cluster:latest \
    /spark/bin/spark-submit \
        --packages org.apache.spark:spark-avro_2.11:2.4.1 \
        --master yarn \
        --deploy-mode cluster \
        --conf "spark.scheduler.listenerbus.eventqueue.capacity"=$LISTENERBUS_CAPACITY \
        --conf "spark.cores.max"=$MAX_CORES \
        --conf "spark.executor.cores"=$EXECUTOR_CORES \
        --conf "spark.executor.memory"=$EXECUTOR_MEMORY \
        --conf "spark.driver.memory"=$DRIVER_MEMORY \
        --py-files listenbrainz_spark_request_consumer.zip \
	spark_manage.py request_consumer
