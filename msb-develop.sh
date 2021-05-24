#!/bin/bash

# ./develop.sh                 Bring up, run the server

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the messybrainz-server source."
    exit -1
fi


COMPOSE_FILE_LOC=docker/docker-compose.yml
COMPOSE_PROJECT_NAME=messybrainz

docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME build && \
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME up
