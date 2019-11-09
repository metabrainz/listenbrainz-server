#!/bin/bash


# stop the request consumer
./stop-request-consumer-container.sh

# stop the spark and hadoop service
docker service rm spark-master hadoop-master
