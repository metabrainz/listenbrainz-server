#!/bin/bash

docker-compose -f docker/docker-compose.labs.api.yml -p listenbrainz "$@"
