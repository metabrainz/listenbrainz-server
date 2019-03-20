#!/bin/bash

cd ..

docker build -t metabrainz/spark-worker -f Dockerfile.worker . && \
    docker push metabrainz/spark-worker
