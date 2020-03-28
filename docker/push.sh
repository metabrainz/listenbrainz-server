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

ENV=${1:-beta}
TAG=${2:-beta}
echo "building for env $ENV tag $TAG"
docker build -t metabrainz/listenbrainz:$TAG --target listenbrainz-prod --build-arg deploy_env=$ENV . && \
    docker push metabrainz/listenbrainz:$TAG
