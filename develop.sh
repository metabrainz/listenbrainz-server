#!/usr/bin/env bash

if [[! -d "docker" ]]; then
    echo "This script should be used from the top level dir of the listenbrainz-recommendation-playground"
    exit -1
fi

docker-compose -f docker/docker-compose.dev.yml -p listenbrainzspark "$@"
