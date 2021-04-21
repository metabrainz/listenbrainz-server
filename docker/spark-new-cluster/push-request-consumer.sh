#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../../"

docker build -t metabrainz/listenbrainz-spark-new-cluster -f Dockerfile.spark.newcluster .
docker push metabrainz/listenbrainz-spark-new-cluster
