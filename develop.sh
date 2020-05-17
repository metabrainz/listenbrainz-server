#!/bin/bash

POSTGRES_LB_URI="postgresql://listenbrainz:listenbrainz@db/listenbrainz"

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

function invoke_docker_compose {
    docker-compose -f docker/docker-compose.yml \
                -p listenbrainz \
                "$@"
}

function invoke_manage {
    invoke_docker_compose run --rm web \
            python3 manage.py \
            "$@"
}

function open_psql_shell {
    invoke_docker_compose run --rm web psql \
        $POSTGRES_LB_URI
}

function npm_install {
    invoke_docker_compose run --rm -e \
                HOME=/tmp static_builder npm install
}

function invoke_docker_compose_spark {
    docker-compose -f docker/docker-compose.spark.yml \
                -p listenbrainzspark \
                "$@"
}

function format_namenode {
    invoke_docker_compose_spark run --rm hadoop-master \
            hdfs namenode -format -nonInteractive -force
}

# Arguments following "manage" are as it is passed to function "invoke_manage" and executed.
# Check on each argument of manage.py is not performed here because with manage.py, develop.sh will expand too.
# Also, if any of the arguments passed to develop.sh which invoke manage.py are incorrect, exception would be raised by manage.py
# so we may skip extra checks in here.
if [ "$1" == "manage" ]; then shift
    echo "Invoking manage.py..."
    invoke_manage "$@"
    exit

elif [ "$1" == "psql" ]; then
    echo "Entering into PSQL shell to query DB..."
    open_psql_shell
    exit

elif [ "$1" == "npm" ]; then
    echo "Installing node dependencies..."
    npm_install
    exit

elif [ "$1" == "spark" ]; then shift
    if [ "$1" == 'format' ]; then
        format_namenode
        exit
    else
        invoke_docker_compose_spark "$@"
        exit
    fi

else
    if [ "$#" == 0 ]; then
        echo "No argument provided. Trying to run docker-compose..."
    else
        echo "Trying to run the passed command with docker-compose..."
    fi
    invoke_docker_compose "$@"
    exit
fi
