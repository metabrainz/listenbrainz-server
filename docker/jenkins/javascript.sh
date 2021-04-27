#!/usr/bin/env bash

# This script is used to run Listenbrainz javascript tests on Jenkins

# Modify these two as needed:
COMPOSE_FILE_LOC="docker/jenkins/docker-compose.unit.yml"
TEST_CONTAINER_NAME="listenbrainz"

COMPOSE_PROJECT_NAME_ORIGINAL="listenbrainzunittest_jenkinsbuild_${BUILD_TAG}"

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_CONTAINER_NAME}_run"

# Record installed version of Docker and Compose with each build
echo "Docker environment:"
docker --version
docker-compose --version

function cleanup {
    # Shutting down all containers associated with this project
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   down --remove-orphans
    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
        | awk '{print $1}' | xargs --no-run-if-empty docker stop
    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
        | awk '{print $1}' | xargs --no-run-if-empty docker rm
}

function run_tests {
    # Create containers
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                    build frontend_tester

    # List images and containers related to this build
    docker images | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'
    docker ps -a | grep $COMPOSE_PROJECT_NAME | awk '{print $0}'

    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --name ${TEST_CONTAINER_REF}_test \
                frontend_tester npm run test:ci
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --name ${TEST_CONTAINER_REF}_lint \
                frontend_tester npm run format:ci
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --name ${TEST_CONTAINER_REF}_typecheck \
                frontend_tester npm run type-check
    docker cp ${TEST_CONTAINER_REF}_test:/code/junit.xml .
    docker cp ${TEST_CONTAINER_REF}_lint:/code/eslint.xml .
}

set -e
cleanup            # Initial cleanup
trap cleanup EXIT  # Cleanup after tests finish running

run_tests
