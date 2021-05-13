#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

rm -r pyspark_venv pyspark_venv.tar.gz listenbrainz_spark_request_consumer.zip

python3 -m venv pyspark_venv
source pyspark_venv/bin/activate
pip install -r requirements_spark.txt
pip install venv-pack
venv-pack -o pyspark_venv.tar.gz

export PYSPARK_DRIVER_PYTHON=python
export PYSPARK_PYTHON=./environment/bin/python

zip -rq listenbrainz_spark_request_consumer.zip listenbrainz_spark/

source spark_config.sh
spark-submit \
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
