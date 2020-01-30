#!/bin/bash

OUTMAIL_DOMAIN=metabrainz.org
MAILNAME=listenbrainz.org
NAME=exim-relay-$MAILNAME
SPOOL_VOLUME_NAME=${2:-exim-relay-spool-$MAILNAME}
TAG=$(echo -n "$MAILNAME"|tr '.' '-')
IMAGE=metabrainz/docker-exim

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

docker pull $IMAGE
docker volume create --driver local --name $SPOOL_VOLUME_NAME
docker run \
    --detach \
    --name $NAME \
    --hostname $(hostname -s).${OUTMAIL_DOMAIN} \
    --env DOMAIN=${MAILNAME} \
    --network spark-network \
    --env GMAIL_GSUITE_RELAY=yes \
    -v ${SPOOL_VOLUME_NAME}:/var/spool/exim4 \
    --publish 25:25 \
    --restart unless-stopped \
    $IMAGE

# start the request consumer (stats, recommendation requests from the main server farm)
./start-request-consumer-container.sh
