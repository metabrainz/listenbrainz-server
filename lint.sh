#!/bin/bash

docker-compose -f docker/docker-compose.yml \
               -p listenbrainz \
               run --rm static_builder npm run format
