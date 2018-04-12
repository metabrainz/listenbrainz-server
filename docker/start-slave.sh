#!/bin/sh

if [ "$#" -ne 1 ]; then
    echo "  Usage: start-node.sh <master ip>"
fi

MASTER_IP=$1

# start the spark worker container
docker pull metabrainz/spark-worker
docker run \
   --name spark-worker \
   --restart=unless-stopped \
   -d \
   --env MASTER_IP="$MASTER_IP" \
   metabrainz/spark-worker
