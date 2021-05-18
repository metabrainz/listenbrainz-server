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
    --cache-from kartik1712/listenbrainz:latest \
    --tag kartik1712/listenbrainz:"$TAG" \
    --target listenbrainz-prod \
    --load \
    --build-arg GIT_COMMIT_SHA="$GIT_COMMIT_SHA" . \
    && docker push kartik1712/listenbrainz:"$TAG"


# Only tag the built image as latest if the TAG matches the
# date pattern (v-YYYY-MM-DD.N) we use for production releases.
if [[ $TAG =~ ^v-[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+$  ]]; then
    docker tag kartik1712/listenbrainz:"$TAG" kartik1712/listenbrainz:latest && \
    docker push kartik1712/listenbrainz:latest
fi
