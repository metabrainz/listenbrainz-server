#!/bin/bash

<<<<<<< HEAD
# ./test.sh                bring up, make database, test, bring down
# for development:
# ./test.sh -u             bring up background and load database if needed
# ./test.sh [params]       run tests, passing optional params to inner test
# ./test.sh -s             stop test containers without removing
# ./test.sh -d             clean test containers

COMPOSE_FILE_LOC=docker/docker-compose.test.yml
COMPOSE_PROJECT_NAME_ORIGINAL=listenbrainz_test

# Project name is sanitized by Compose, so we need to do the same thing.
# See https://github.com/docker/compose/issues/2119.
COMPOSE_PROJECT_NAME=$(echo $COMPOSE_PROJECT_NAME_ORIGINAL | awk '{print tolower($0)}' | sed 's/[^a-z0-9]*//g')
TEST_CONTAINER_NAME=listenbrainz
TEST_CONTAINER_REF="${COMPOSE_PROJECT_NAME}_${TEST_CONTAINER_NAME}_1"

#docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME build
#    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
#        | awk '{print $1}' | xargs -r --no-run-if-empty docker stop
#    docker ps -a --no-trunc  | grep $COMPOSE_PROJECT_NAME \
#        | awk '{print $1}' | xargs -r --no-run-if-empty docker rm


if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi


function bring_up_db {
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME up -d db influx redis rabbitmq
}

function setup {
    echo "Running setup"
    # PostgreSQL Database initialization
    docker-compose -f $COMPOSE_FILE_LOC -p $COMPOSE_PROJECT_NAME run --rm listenbrainz dockerize -wait tcp://db:5432 -timeout 60s \
                  -wait tcp://influx:8086 -timeout 60s \
                  -wait tcp://rabbitmq:5672 -timeout 60s \
                bash -c "python3 manage.py init_db --create-db && \
                         python3 manage.py init_msb_db --create-db && \
                         python3 manage.py init_influx"
}

function is_db_running {
    # Check if the database container is running
    containername="${COMPOSE_PROJECT_NAME}_db_1"
    res=`docker ps --filter "name=$containername" --filter "status=running" -q`
    if [ -n "$res" ]; then
        return 0
    else
        return 1
    fi
}

function is_db_exists {
    containername="${COMPOSE_PROJECT_NAME}_db_1"
    res=`docker ps --filter "name=$containername" --filter "status=exited" -q`
    if [ -n "$res" ]; then
        return 0
    else
        return 1
    fi
}

function stop {
    echo "stop"
    # Stopping all containers associated with this project
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
               stop
}

function dcdown {
    # Shutting down all containers associated with this project
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
               down
}

# Exit immediately if a command exits with a non-zero status.
# set -e
#trap cleanup EXIT  # Cleanup after tests finish running

if [ "$1" == "-s" ]; then
    echo "Stopping containers"
    stop
    exit 0
fi

if [ "$1" == "-d" ]; then
    echo "Running docker-compose down"
    dcdown
    exit 0
fi

# if -u flag, bring up db, run setup, quit
if [ "$1" == "-u" ]; then
    is_db_exists
    DB_EXISTS=$?
    is_db_running
    DB_RUNNING=$?
    if [ $DB_EXISTS -eq 0 -o $DB_RUNNING -eq 0 ]; then
        echo "Database is already up, doing nothing"
    else
        echo "Bringing up DB"
        bring_up_db
        setup
    fi
    exit 0
fi

is_db_exists
DB_EXISTS=$?
is_db_running
DB_RUNNING=$?
if [ $DB_EXISTS -eq 1 -a $DB_RUNNING -eq 1 ]; then
    # If no containers, run setup then run tests, then bring down
    bring_up_db
    setup
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   run --rm listenbrainz py.test "$@"
    dcdown
else
    # Else, we have containers, just run tests
    docker-compose -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   run --rm listenbrainz py.test "$@"
fi
=======
>>>>>>> labs/master
