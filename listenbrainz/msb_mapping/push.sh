#!/bin/bash
#
# Build production image from the currently checked out version
# of ListenBrainz and push it to Docker Hub, with an optional
# tag (which defaults to "latest")
#
# Usage:
#   $ ./push.sh [tag]


TAG=${1:-beta}
echo "building for tag $TAG"
docker build -t metabrainz/listenbrainz-msb-mapper:$TAG . && \
    docker push metabrainz/listenbrainz-msb-mapper:$TAG
