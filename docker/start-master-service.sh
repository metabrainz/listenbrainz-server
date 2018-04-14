#!/bin/bash


docker network create -d overlay spark-network

docker node update --label-add type=master `hostname`
docker service create --replicas 1 \
    --name spark-master \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    -p 7077:7077 \
    -p 6066:6066 \
    -p 8080:8080 \
    metabrainz/spark-master
