#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: start-worker-service.sh <replicas>"
    exit
fi

REPLICAS=$1

docker service create --replicas $REPLICAS \
    --env NODE_TYPE="worker" \
    --network spark-network \
    --name yarn-workers \
    metabrainz/hadoop-yarn:beta

docker service create \
    --replicas $REPLICAS \
    --name spark-workers \
    --network spark-network \
    --env SPARK_NO_DAEMONIZE=1 \
    metabrainz/spark-worker
