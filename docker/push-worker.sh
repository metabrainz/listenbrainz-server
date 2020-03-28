#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"
docker build -t metabrainz/spark-worker --target metabrainz-spark-worker -f Dockerfile.spark . && \
    docker push metabrainz/spark-worker
