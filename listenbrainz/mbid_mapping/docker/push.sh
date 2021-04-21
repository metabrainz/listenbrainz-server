#!/bin/bash
#
# Build production image from the currently checked out version
# of ListenBrainz and push it to Docker Hub, with an optional
# tag (which defaults to "latest")
#
# Usage:
#   $ ./push.sh [tag]


cd "$(dirname "${BASH_SOURCE[0]}")/../"

git describe --tags --dirty --always > .git-version

TAG=${1:-prod}
echo "building tag $TAG"
docker build -t metabrainz/listenbrainz-mbid-mapping:$TAG --target mbid-mapping-prod . && \
    docker push metabrainz/listenbrainz-mbid-mapping:$TAG
