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

echo "building for tag $TAG"

docker buildx build \
    --cache-from metabrainz/listenbrainz:latest \
    --tag metabrainz/listenbrainz:"$TAG" \
    --target listenbrainz-prod \
    --push \
    --build-arg GIT_COMMIT_SHA="$GIT_COMMIT_SHA" .


# Only tag the built image as latest if the TAG matches the
# date pattern (v-YYYY-MM-DD.N) we use for production releases.
if [[ $TAG =~ ^v-[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+$  ]]; then
    docker tag metabrainz/listenbrainz:"$TAG" metabrainz/listenbrainz:latest && \
    docker push metabrainz/listenbrainz:latest
fi
