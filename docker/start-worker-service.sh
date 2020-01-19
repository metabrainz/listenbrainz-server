#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: start-worker-service.sh <replicas>"
    exit
fi

docker pull metabrainz/spark-worker

REPLICAS=$1

docker service create --replicas $REPLICAS \
    --env NODE_TYPE="worker" \
    --network spark-network \
    --name hadoop-workers \
    --mount type=volume,source=hdfs-volume,destination=/home/hadoop/hdfs \
    metabrainz/hadoop-yarn:beta

docker service create \
    --replicas $REPLICAS \
    --name spark-workers \
    --network spark-network \
    --env SPARK_NO_DAEMONIZE=1 \
    --mount type=volume,source=spark-volume,destination=/home/hadoop/spark \
    metabrainz/spark-worker
