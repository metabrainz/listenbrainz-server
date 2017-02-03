#!/bin/bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

docker-compose -f docker/docker-compose.test.yml -p listenbrainz_test down
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_test build 
docker-compose -f docker/docker-compose.test.yml -p listenbrainz_test up
