#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build -t metabrainz/spark-master --target metabrainz-spark-master . && \
    docker push metabrainz/spark-master
