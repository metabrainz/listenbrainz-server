#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build -t metabrainz/spark-master -f Dockerfile.master . && \
    docker push metabrainz/spark-master
