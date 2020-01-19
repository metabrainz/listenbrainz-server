#!/bin/bash

docker build --target metabrainz-spark-request-consumer -t metabrainz/listenbrainz-spark-request-consumer .
docker push metabrainz/listenbrainz-spark-request-consumer
