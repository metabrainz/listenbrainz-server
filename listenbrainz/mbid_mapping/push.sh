#!/bin/bash
#
# Build production image from the currently checked out version
# of the MBID mapping and push it to Docker Hub, with an optional
# tag (which defaults to "beta")
#
# Usage:
#   $ ./push.sh [tag]

TAG=${1:-beta}
echo "building for tag $TAG"
docker build -t metabrainz/listenbrainz-mbid-mapping:$TAG -f Dockerfile.prod . && \
    docker push metabrainz/listenbrainz-mbid-mapping:$TAG
