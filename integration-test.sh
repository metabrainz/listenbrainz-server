#!/bin/bash

COMPOSE_FILE_LOC=docker/docker-compose.integration.yml
COMPOSE_PROJECT_NAME_ORIGINAL=listenbrainz_int

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_NAME=listenbrainz
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_CONTAINER_NAME}_1"

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

echo "Take down old containers"
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME down

echo "Build current setup"
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME build

echo "Running setup"
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --rm listenbrainz dockerize -wait tcp://db:5432 -timeout 60s \
                  -wait tcp://influx:8086 -timeout 60s \
                bash -c "python3 manage.py init_db --create-db && \
                         python3 manage.py init_msb_db --create-db && \
                         python3 manage.py init_influx"


echo "Bring containers up"
docker-compose -f docker/docker-compose.integration.yml -p $COMPOSE_PROJECT_NAME up -d db influx redis influx_writer rabbitmq

echo "Start running tests"
docker-compose -f docker/docker-compose.integration.yml \
               -p $COMPOSE_PROJECT_NAME \
               run --rm listenbrainz dockerize \
                                     -wait tcp://db:5432 -timeout 60s \
                                     -wait tcp://influx:8086 -timeout 60s \
                                     -wait tcp://redis:6379 -timeout 60s \
                                     -wait tcp://rabbitmq:5672 -timeout 60s \
                                     bash -c "py.test listenbrainz/tests/integration"
echo "Take down containers"
docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME down
