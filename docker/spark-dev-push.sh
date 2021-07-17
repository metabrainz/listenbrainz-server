#!/bin/bash
#
# Build base metabrainz spark image (only used in development and testing)
# and push it to Docker Hub, with an optional tag (which defaults to "latest")
#
# Usage:
#   $ ./spark-dev-push.sh [tag]

set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

TAG=${1:-latest}

docker build --tag metabrainz/listenbrainz-spark-base:"$TAG" -f Dockerfile.spark.base . \
  && docker push metabrainz/listenbrainz-spark-base
