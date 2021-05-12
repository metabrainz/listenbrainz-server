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

git describe --tags --dirty --always > .git-version

TAG=${1:-beta}
echo "building for tag $TAG"
docker build \
        --cache-from kartik1712/listenbrainz:latest \
        --tag kartik1712/listenbrainz:"$TAG" \
        --tag kartik1712/listenbrainz:latest \
        --target listenbrainz-prod \
        --build-arg GIT_COMMIT_SHA="$(git describe --tags --dirty --always)" . && \
    docker push kartik1712/listenbrainz:"$TAG" && \
    docker push kartik1712/listenbrainz:latest
