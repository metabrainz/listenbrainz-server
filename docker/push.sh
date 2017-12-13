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

TAG=${1:-latest}
docker build -t metabrainz/listenbrainz:$TAG -f Dockerfile.prod .
docker push metabrainz/listenbrainz:$TAG
