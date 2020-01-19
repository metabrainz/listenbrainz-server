#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"
docker build -t metabrainz/spark-worker --target metabrainz-spark-worker . && \
    docker push metabrainz/spark-worker
