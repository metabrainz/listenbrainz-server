#!/bin/bash

# Before this runs, we need to also do these:
#docker volume create hdfs-volume
#docker run metabrainz/hadoop-yarn:beta /usr/local/hadoop/bin/hdfs namenode -format


docker network create -d overlay spark-network

docker node update --label-add type=master `hostname`

docker service create --replicas 1 \
    --name hadoop-master \
    --hostname hadoop-master \
    --env NODE_TYPE="master" \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    -p published=8031,target=8031,mode=host \
    -p published=8088,target=8088,mode=host \
    -p published=9000,target=9000,mode=host \
    -p published=50070,target=50070,mode=host \
    --mount type=volume,source=hdfs-volume,destination=/home/hadoop/hdfs \
    metabrainz/hadoop-yarn:beta

docker service create --replicas 1 \
    --name spark-master \
    --hostname spark-master \
    --network spark-network \
    --constraint 'node.labels.type == master' \
    -p published=7077,target=7077,mode=host \
    -p published=6066,target=6066,mode=host \
    -p published=8080,target=8080,mode=host \
    --env SPARK_NO_DAEMONIZE=1 \
    metabrainz/spark-master
