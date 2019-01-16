#!/bin/bash

docker build -t metabrainz/listenbrainz-spark-jobs -f Dockerfile.jobs . && \
    docker push metabrainz/listenbrainz-spark-jobs
