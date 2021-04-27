#!/bin/bash

docker stop spark-request-consumer
docker rm spark-request-consumer
rm -r pyspark_venv pyspark_venv.tar.gz listenbrainz_spark_request_consumer.zip

