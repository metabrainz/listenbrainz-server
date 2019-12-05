#!/bin/bash

docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test run --rm hadoop-master hdfs namenode -format -nonInteractive -force
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test up -d hadoop-master datanode
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test up test
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_labs_test down
