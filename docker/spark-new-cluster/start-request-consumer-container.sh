#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../../"

source spark_config.sh

CONTAINER_NAME="spark-request-consumer"

docker pull metabrainz/listenbrainz-spark-new-cluster:latest

python3 -m venv pyspark_venv
source pyspark_venv/bin/activate
pip install -r requirements_spark.txt
pip uninstall pyspark py4j -y
pip install venv-pack
venv-pack -o pyspark_venv.tar.gz

export PYSPARK_DRIVER_PYTHON=python
export PYSPARK_PYTHON=./environment/bin/python

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/

docker run \
    -d \
    -e PYSPARK_DRIVER_PYTHON \
    -e PYSPARK_PYTHON \
    -v /spark:/spark \
    -v /hadoop:/hadoop \
    -v /usr/lib/jvm/adoptopenjdk-11-hotspot-amd64:/usr/lib/jvm/adoptopenjdk-11-hotspot-amd64 \
    -v `pwd`:/rec \
    --network host \
    --name $CONTAINER_NAME \
    metabrainz/listenbrainz-spark-new-cluster:latest \
    /spark/bin/spark-submit \
        --packages org.apache.spark:spark-avro_2.12:3.1.1 \
        --master yarn \
        --conf "spark.yarn.dist.archives"=pyspark_venv.tar.gz#environment \
        --conf "spark.scheduler.listenerbus.eventqueue.capacity"=$LISTENERBUS_CAPACITY \
        --conf "spark.cores.max"=$MAX_CORES \
        --conf "spark.executor.cores"=$EXECUTOR_CORES \
        --conf "spark.executor.memory"=$EXECUTOR_MEMORY \
        --conf "spark.driver.memory"=$DRIVER_MEMORY \
        --py-files listenbrainz_spark_request_consumer.zip \
	spark_manage.py request_consumer
