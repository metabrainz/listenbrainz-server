#!/bin/bash

# NOTE:
# If the hadoop-master container seems to keep dying because "Namenode is not formatted" or similar
# format it using the following command
# `docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test run --rm hadoop-master hdfs namenode -format`

docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test up -d hadoop-master datanode
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test up test
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test down
