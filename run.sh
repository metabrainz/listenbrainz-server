#!/bin/bash

if [ "$#" -eq 0 ]; then
    echo "Usage: run.sh <cmd_to_run> ..."
    exit
fi

source config.sh

docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
docker pull metabrainz/listenbrainz-spark:latest
docker run \
    -v `pwd`:/rec \
    --network spark-network \
    --name $CONTAINER_NAME \
    metabrainz/listenbrainz-spark:latest \
    "$@"
