#!/bin/bash
#
# Build production image from the currently checked out version
# of ListenBrainz and push it to Docker Hub, with an optional
# tag (which defaults to "beta")
#
# Usage:
#   $ ./push.sh [tag]

set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

GIT_COMMIT_SHA="$(git describe --tags --dirty --always)"
echo "$GIT_COMMIT_SHA" > .git-version

TAG=${1:-beta}

function build_and_push_image {
    echo "building for tag $1"
    docker build \
        --tag metabrainz/listenbrainz:"$1" \
        --target listenbrainz-prod \
        --build-arg GIT_COMMIT_SHA="$GIT_COMMIT_SHA" . && \
    docker push metabrainz/listenbrainz:"$1"
}

build_and_push_image "$TAG"
