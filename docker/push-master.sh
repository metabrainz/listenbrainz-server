#!/bin/bash

docker build -t metabrainz/spark-master -f Dockerfile.master . && \
    docker push metabrainz/spark-master
