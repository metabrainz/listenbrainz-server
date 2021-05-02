#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../../"

docker build --target metabrainz-spark-prod -t metabrainz/listenbrainz-spark-new-cluster -f Dockerfile.spark .
docker push metabrainz/listenbrainz-spark-new-cluster
