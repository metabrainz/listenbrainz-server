#!/bin/bash

docker build -t metabrainz/spark-worker -f Dockerfile . && \
    docker push metabrainz/spark-worker
