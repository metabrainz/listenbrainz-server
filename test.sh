#!/bin/bash

# Github Actions automatically sets the CI environment variable. We use this variable to detect if the script is running
# inside a CI environment and modify its execution as needed.
if [ "$CI" == "true" ] ; then
    echo "Running in CI mode"
fi

# BACKEND TESTS
# ./test.sh                build unit test containers, bring up, make database, test, bring down
# for development:
# ./test.sh -u             build unit test containers, bring up background and load database if needed
# ./test.sh [path-to-tests-file-or-directory]  # run specific tests
# ./test.sh -s             stop unit test containers without removing
# ./test.sh -d             clean unit test containers

# FRONTEND TESTS
# ./test.sh fe             run frontend tests
# ./test.sh fe -u          run frontend tests, update snapshots
# ./test.sh fe -b          build frontend test containers
# ./test.sh fe -t          run type-checker
# ./test.sh fe -f          run linters

# SPARK TESTS
# ./test.sh spark          run spark tests
# ./test.sh spark -b       build spark test containers

COMPOSE_FILE_LOC=docker/docker-compose.test.yml
COMPOSE_PROJECT_NAME=listenbrainz_test

SPARK_COMPOSE_FILE_LOC=docker/docker-compose.spark.yml
SPARK_COMPOSE_PROJECT_NAME=listenbrainz_spark_test

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit 255
fi

echo "Checking docker compose version"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

if [[ -f .env ]]; then
    . .env
    if [ -z $LB_DOCKER_USER ]; then
        echo LB_DOCKER_USER=$(id -u) >> .env
    fi
    if [ -z $LB_DOCKER_GROUP ]; then
        echo LB_DOCKER_GROUP=$(id -g) >> .env
    fi
else
    echo LB_DOCKER_USER=$(id -u) >> .env
    echo LB_DOCKER_GROUP=$(id -g) >> .env
fi

function invoke_docker_compose {
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE_LOC \
                   -p $COMPOSE_PROJECT_NAME \
                   --env-file .env \
                   "$@"
}

function invoke_docker_compose_spark {
    $DOCKER_COMPOSE_CMD -f $SPARK_COMPOSE_FILE_LOC \
                   -p $SPARK_COMPOSE_PROJECT_NAME \
                   "$@"
}

function docker_compose_run {
    invoke_docker_compose run --rm --user "$(id -u)":"$(id -g)" "$@"
}

function docker_compose_run_fe {
  invoke_docker_compose run --rm frontend_tester npm run "$@"
}

function docker_compose_run_spark {
    # We run spark tests as root and not the local user due to the requirement for
    # the uid to exist as a real user
    invoke_docker_compose_spark run --rm "$@"
}

function build_unit_containers {
    invoke_docker_compose build listenbrainz
}

function bring_up_unit_db {
    invoke_docker_compose up -d lb_db redis rabbitmq couchdb timescale_writer background_tasks websockets
}

function unit_setup {
    echo "Running setup"
    # PostgreSQL Database initialization
    docker_compose_run listenbrainz dockerize \
                  -wait tcp://lb_db:5432 -timeout 60s \
                  -wait tcp://rabbitmq:5672 -timeout 60s \
                  -wait tcp://couchdb:5984 -timeout 60s \
                bash -c "python3 manage.py init_db --create-db && \
                         python3 manage.py init_ts_db --create-db"
}

function is_unit_db_running {
    # Check if the database container is running
    containername="${COMPOSE_PROJECT_NAME}-lb_db-1"
    res=$(docker ps --filter "name=$containername" --filter "status=running" -q)
    if [ -n "$res" ]; then
        return 0
    else
        return 1
    fi
}

function unit_stop {
    # Stopping all unit test containers associated with this project
    invoke_docker_compose stop
}

function unit_dcdown {
    # Shutting down all unit test containers associated with this project
    invoke_docker_compose down
}

function build_frontend_containers {
    invoke_docker_compose build frontend_tester
}

function update_snapshots {
    docker_compose_run_fe test:update-snapshots
}

function run_lint_check {
    if [ "$CI" == "true" ] ; then
        command="format:ci"
    else
        command="format"
    fi

    docker_compose_run_fe $command
}

function run_frontend_tests {
    if [ "$CI" == "true" ] ; then
        command="test:ci"
    else
        command="test"
    fi
    docker_compose_run_fe $command
}

function run_type_check {
    docker_compose_run_fe type-check
}

function spark_setup {
    echo "Running spark test setup"
    invoke_docker_compose_spark up -d namenode datanode
}

function build_spark_containers {
    invoke_docker_compose_spark build namenode
}

function spark_dcdown {
    # Shutting down all spark test containers associated with this project
    invoke_docker_compose_spark down
}

# Exit immediately if a command exits with a non-zero status.
# set -e
# trap cleanup EXIT  # Cleanup after tests finish running

if [ "$1" == "spark" ]; then
    if [ "$2" == "-b" ]; then
        echo "Building containers"
        build_spark_containers
        exit 0
    fi

    spark_setup
    echo "Running tests"
    docker_compose_run_spark request_consumer
    RET=$?
    spark_dcdown
    exit $RET
fi

if [ "$1" == "fe" ]; then
    if [ "$2" == "-u" ]; then
        echo "Running tests and updating snapshots"
        update_snapshots
        exit 0
    fi

    if [ "$2" == "-b" ]; then
        echo "Building containers"
        build_frontend_containers
        exit 0
    fi

    if [ "$2" == "-t" ]; then
        echo "Running type checker"
        run_type_check
        exit $?
    fi

    if [ "$2" == "-f" ]; then
        echo "Running linters"
        run_lint_check
        exit $?
    fi

    echo "Running tests"
    run_frontend_tests
    exit $?
fi

if [ "$1" == "-s" ]; then
    echo "Stopping unit test containers"
    unit_stop
    exit 0
fi

if [ "$1" == "-d" ]; then
    echo "Running docker compose down"
    unit_dcdown
    exit 0
fi

# if -u flag, bring up db, run setup, quit
if [ "$1" == "-u" ]; then
    is_unit_db_running
    DB_RUNNING=$?
    if [ $DB_RUNNING -eq 0 ]; then
        echo "Database is already up, doing nothing"
    else
        echo "Building containers"
        build_unit_containers
        echo "Bringing up DB"
        bring_up_unit_db
        unit_setup
    fi
    exit 0
fi

is_unit_db_running
DB_RUNNING=$?
if [ $DB_RUNNING -eq 1 ] ; then
    # If no containers, build them, run setup then run tests, then bring down
    build_unit_containers
    bring_up_unit_db
    unit_setup
    echo "Running tests"
    docker_compose_run listenbrainz pytest "$@"
    RET=$?
    exit $RET
else
    # Else, we have containers, just run tests
    echo "Running tests"
    docker_compose_run listenbrainz pytest "$@"
    exit $?
fi
