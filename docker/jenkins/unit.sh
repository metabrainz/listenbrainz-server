#!/usr/bin/env bash

# This script is used to run Listenbrainz unit tests on Jenkins

# Modify these two as needed:
COMPOSE_FILE_LOC="docker/jenkins/docker-compose.unit.yml"
TEST_CONTAINER_NAME="listenbrainz"

COMPOSE_PROJECT_NAME_ORIGINAL="listenbrainzunittest_jenkinsbuild_${BUILD_TAG}"

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_CONTAINER_NAME}_run_1"

# Record installed version of Docker and Compose with each build
echo "Docker environment:"
docker --version
docker-compose --version

function cleanup {
    # Shutting down all containers associated with this project
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   down --remove-orphans
    # Untag LB images that were built before this test run
    docker image rm $(docker images --filter="before=$COMPOSE_PROJECT_NAME_listenbrainz" --filter "label=org.label-schema.name=ListenBrainz" --format '{{.Repository}}:{{.Tag}}')
}

function run_tests {
    # copy config before build, it's needed in all containers
    cp listenbrainz/config.py.sample listenbrainz/config.py

    # Create containers
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                    build

    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   up -d db redis rabbitmq

    # List images and containers related to this build
    docker images | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'
    docker ps -a | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'

    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --rm listenbrainz \
      dockerize \
      -wait tcp://db:5432 -timeout 60s bash -c \
      "ls && python3 manage.py init_db --create-db && \
       python3 manage.py init_msb_db --create-db && \
       python3 manage.py init_ts_db --create-db"

    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --name $TEST_CONTAINER_REF \
                listenbrainz \
                dockerize \
                -wait tcp://db:5432 -timeout 60s \
                -wait tcp://redis:6379 -timeout 60s \
                py.test --junitxml=/data/test_report.xml \
                        --cov-report xml:/data/coverage.xml
}

function  extract_results {
    docker cp ${TEST_CONTAINER_REF}:/data/test_report.xml . || true
    docker cp ${TEST_CONTAINER_REF}:/data/coverage.xml . || true
}

set -e
cleanup            # Initial cleanup
trap cleanup EXIT  # Cleanup after tests finish running

run_tests
extract_results
