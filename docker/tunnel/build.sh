#!/bin/bash
#
# Build image from the currently checked out version of the MetaBrainz website
# and push it to the Docker Hub, with an optional tag (by default "latest").
#
# Usage:
#   $ ./push.sh [tag]

TAG_PART=${1:-latest}
docker build -t metabrainz/listenbrainz-tunnel:$TAG_PART .
