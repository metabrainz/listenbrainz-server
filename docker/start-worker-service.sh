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
    --env MASTER_IP=195.201.112.36 \
    metabrainz/spark-worker
