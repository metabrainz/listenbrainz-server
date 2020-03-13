#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build -t metabrainz/listenbrainz-spark --target metabrainz-spark-jobs -f Dockerfile.spark .
docker push metabrainz/listenbrainz-spark
