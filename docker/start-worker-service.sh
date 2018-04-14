#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: start-worker-service.sh <replicas>"
    exit
fi

REPLICAS=$1

docker service create \
    --replicas $REPLICAS \
    --name spark-workers \
    --network spark-network \
    --env SPARK_NO_DAEMONIZE=1 \
    metabrainz/spark-worker
