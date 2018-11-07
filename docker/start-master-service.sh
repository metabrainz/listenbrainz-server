#!/bin/bash


docker network create -d overlay spark-network

docker node update --label-add type=master `hostname`

docker service create --replicas 1 \
    --name hadoop-master \
    --hostname hadoop-master \
    --env NODE_TYPE="master" \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    -p 50070:50070 \
    -p 8088:8088 \
    -p 9000:9000 \
    metabrainz/hadoop-yarn:beta

docker service create --replicas 1 \
    --name spark-master \
    --hostname spark-master \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    -p 7077:7077 \
    -p 6066:6066 \
    -p 8080:8080 \
    --env SPARK_NO_DAEMONIZE=1 \
    metabrainz/spark-master
