#!/bin/bash

docker service rm spark-master hadoop-master

# stop the request consumer
./stop-request-consumer-container.sh
