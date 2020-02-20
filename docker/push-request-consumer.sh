#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build --target metabrainz-spark-request-consumer -t metabrainz/listenbrainz-spark-request-consumer -f Dockerfile.spark .
docker push metabrainz/listenbrainz-spark-request-consumer
