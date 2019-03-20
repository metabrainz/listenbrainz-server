#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"
docker build -t metabrainz/spark-worker -f Dockerfile.worker . && \
    docker push metabrainz/spark-worker
