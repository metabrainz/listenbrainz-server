#!/bin/bash

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

function invoke_docker_compose_spark {
    docker-compose -f docker/docker-compose.spark.yml \
                -p listenbrainzspark \
                "$@"
}

function format_namenode_and_datanode {
    docker-compose -f docker/docker-compose.spark.yml \
        -p listenbrainzspark run --rm hadoop-master hdfs namenode \
        -format -nonInteractive -force
}

if [ "$1" == "format" ]; then shift
    format_namenode_and_datanode "$@"
    exit
else
    invoke_docker_compose_spark "$@"
    exit
fi
