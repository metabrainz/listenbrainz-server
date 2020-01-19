#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../"

docker build -t metabrainz/listenbrainz-spark --target metabrainz-spark-jobs .
docker push metabrainz/listenbrainz-spark
