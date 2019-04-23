#!/bin/bash

# Before this runs, make sure to run set-master-node.sh
docker pull metabrainz/spark-master

docker service create --replicas 1 \
    --name hadoop-master \
    --hostname hadoop-master \
    --env NODE_TYPE="master" \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    --mount type=volume,source=hdfs-volume,destination=/home/hadoop/hdfs \
    metabrainz/hadoop-yarn:beta

docker service create --replicas 1 \
    --name spark-master \
    --hostname spark-master \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    --env SPARK_NO_DAEMONIZE=1 \
    --mount type=volume,source=spark-volume,destination=/home/hadoop/spark \
    metabrainz/spark-master
