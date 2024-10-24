#!/bin/bash

POSTGRES_LB_URI="postgresql://listenbrainz:listenbrainz@lb_db/listenbrainz"
SQLALCHEMY_TIMESCALE_URI="postgresql://listenbrainz_ts:listenbrainz_ts@lb_db/listenbrainz_ts"

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
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
    exec $DOCKER_COMPOSE_CMD -f docker/docker-compose.yml \
                -p listenbrainz \
                --env-file .env \
                "$@"
}

function invoke_manage {
    invoke_docker_compose run  --rm web \
            python3 manage.py \
            "$@"
}

function open_psql_shell {
    invoke_docker_compose run --rm web psql \
        ${POSTGRES_LB_URI}
}

function open_timescale_shell {
    invoke_docker_compose run --rm web psql \
        ${SQLALCHEMY_TIMESCALE_URI}
}

function invoke_docker_compose_spark {
    exec $DOCKER_COMPOSE_CMD -f docker/docker-compose.spark.yml -f docker/docker-compose.spark.override.yml \
                -p listenbrainzspark \
                "$@"
}

function format_namenode {
    # run in a subshell to swallow the exec
    (invoke_docker_compose_spark down)
    docker volume rm -f listenbrainzspark_datanode
    docker volume rm -f listenbrainzspark_namenode
    invoke_docker_compose_spark run --rm namenode \
            hdfs namenode -format -nonInteractive -force
}

# Arguments following "manage" are passed to manage.py inside a new web container.
if [[ "$1" == "manage" ]]; then shift
    echo "Running manage.py..."
    invoke_manage "$@"
elif [[ "$1" == "bash" ]]; then
    echo "Running bash..."
    invoke_docker_compose run --rm web bash
elif [[ "$1" == "shell" ]]; then
    echo "Running flask shell..."
    invoke_docker_compose run --rm web flask shell
elif [[ "$1" == "redis" ]]; then
    echo "Running redis shell..."
    invoke_docker_compose exec redis redis-cli
elif [[ "$1" == "psql" ]]; then
    echo "Connecting to postgresql..."
    open_psql_shell
elif [[ "$1" == "timescale" ]]; then
    echo "Connecting to timescale..."
    open_timescale_shell
elif [[ "$1" == "spark" ]]; then shift
    if [[ "$1" == 'format' ]]; then
        format_namenode
    else
        invoke_docker_compose_spark "$@"
    fi
else
    echo "Running docker-compose with the given command..."
    invoke_docker_compose "$@"
fi
