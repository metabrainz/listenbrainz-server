#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build -t metabrainz/listenbrainz-spark -f Dockerfile.jobs .
docker push metabrainz/listenbrainz-spark
