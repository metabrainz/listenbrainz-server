#!/bin/bash
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build \
  --target metabrainz-spark-prod \
  -t metabrainz/listenbrainz-spark-new-cluster \
  -f Dockerfile.spark \
  --build-arg GIT_COMMIT_SHA="$(git describe --tags --dirty --always)" \
  .
docker push metabrainz/listenbrainz-spark-new-cluster
