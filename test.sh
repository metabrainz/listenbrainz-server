#!/bin/bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

docker-compose -f docker/docker-compose.test.yml down
docker-compose -f docker/docker-compose.test.yml build 
docker-compose -f docker/docker-compose.test.yml up
