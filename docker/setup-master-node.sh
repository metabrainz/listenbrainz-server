#!/bin/bash

# After docker is installed, run this script

docker volume create --driver local hdfs-volume
docker volume create --driver local spark-volume
docker run \
   --mount type=volume,source=hdfs-volume,destination=/home/hadoop/hdfs \
   metabrainz/hadoop-yarn:beta /usr/local/hadoop/bin/hdfs namenode -format

docker network create --attachable -d overlay spark-network
docker node update --label-add type=master `hostname`
