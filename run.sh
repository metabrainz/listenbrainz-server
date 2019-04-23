#!/bin/bash

if [ "$#" -eq 0 ]; then
    echo "Usage: run.sh <cmd_to_run> ..."
    exit
fi

docker stop listenbrainz-jobs-param
docker rm listenbrainz-jobs-param
docker pull metabrainz/listenbrainz-spark:latest
docker run \
    -v `pwd`:/rec \
    --network spark-network \
    --name listenbrainz-jobs-param \
    metabrainz/listenbrainz-spark:latest \
    "$@"
