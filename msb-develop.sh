#!/bin/bash

# ./develop.sh                 Bring up, run the server

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the messybrainz-server source."
    exit -1
fi


COMPOSE_FILE_LOC=docker/docker-compose.yml
COMPOSE_PROJECT_NAME_ORIGINAL=messybrainz

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_NAME=messybrainz
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_CONTAINER_NAME}_1"

docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME build && \
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME up
