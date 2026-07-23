#!/bin/bash

# Sync built ListenBrainz static assets to StaticBrainz.
#
# Expected configuration, either from the environment or admin/config.sh:
#   STATICBRAINZ_SERVERS: space-separated host:port list
#   RSYNC_STATICBRAINZ_KEY: SSH private key path
#
# Optional configuration:
#   STATICBRAINZ_SOURCE_DIR: local source directory, defaults to /static
#   STATICBRAINZ_DESTINATION_DIR: remote destination, defaults to ./
#   STATICBRAINZ_RSYNC_OPTIONS: rsync options, defaults to mirroring the source tree
#   STATICBRAINZ_PRECOMPRESS: set to 0 to skip gzip sidecar creation

set -euo pipefail

unset SSH_AUTH_SOCK

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT"

ENV_STATICBRAINZ_SERVERS=${STATICBRAINZ_SERVERS:-}
ENV_RSYNC_STATICBRAINZ_KEY=${RSYNC_STATICBRAINZ_KEY:-}
ENV_STATICBRAINZ_SOURCE_DIR=${STATICBRAINZ_SOURCE_DIR:-}
ENV_STATICBRAINZ_DESTINATION_DIR=${STATICBRAINZ_DESTINATION_DIR:-}
ENV_STATICBRAINZ_RSYNC_OPTIONS=${STATICBRAINZ_RSYNC_OPTIONS:-}
ENV_STATICBRAINZ_PRECOMPRESS=${STATICBRAINZ_PRECOMPRESS:-}

if [ -f admin/config.sh ]; then
    source admin/config.sh
fi
source admin/functions.sh

if [ -n "$ENV_STATICBRAINZ_SERVERS" ]; then
    STATICBRAINZ_SERVERS=$ENV_STATICBRAINZ_SERVERS
fi
if [ -n "$ENV_RSYNC_STATICBRAINZ_KEY" ]; then
    RSYNC_STATICBRAINZ_KEY=$ENV_RSYNC_STATICBRAINZ_KEY
fi
if [ -n "$ENV_STATICBRAINZ_SOURCE_DIR" ]; then
    STATICBRAINZ_SOURCE_DIR=$ENV_STATICBRAINZ_SOURCE_DIR
fi
if [ -n "$ENV_STATICBRAINZ_DESTINATION_DIR" ]; then
    STATICBRAINZ_DESTINATION_DIR=$ENV_STATICBRAINZ_DESTINATION_DIR
fi
if [ -n "$ENV_STATICBRAINZ_RSYNC_OPTIONS" ]; then
    STATICBRAINZ_RSYNC_OPTIONS=$ENV_STATICBRAINZ_RSYNC_OPTIONS
fi
if [ -n "$ENV_STATICBRAINZ_PRECOMPRESS" ]; then
    STATICBRAINZ_PRECOMPRESS=$ENV_STATICBRAINZ_PRECOMPRESS
fi

STATICBRAINZ_SOURCE_DIR=${STATICBRAINZ_SOURCE_DIR:-/static}
STATICBRAINZ_DESTINATION_DIR=${STATICBRAINZ_DESTINATION_DIR:-./}
STATICBRAINZ_RSYNC_OPTIONS=${STATICBRAINZ_RSYNC_OPTIONS:---recursive --times --compress}
STATICBRAINZ_PRECOMPRESS=${STATICBRAINZ_PRECOMPRESS:-1}

if [ -z "${STATICBRAINZ_SERVERS:-}" ]; then
    echo "STATICBRAINZ_SERVERS must be set to a space-separated host:port list"
    exit 1
fi

if [ -z "${RSYNC_STATICBRAINZ_KEY:-}" ]; then
    echo "RSYNC_STATICBRAINZ_KEY must be set to the SSH private key path"
    exit 1
fi

if [ ! -d "$STATICBRAINZ_SOURCE_DIR" ]; then
    echo "Static assets source directory does not exist: $STATICBRAINZ_SOURCE_DIR"
    exit 1
fi

if [ "$STATICBRAINZ_PRECOMPRESS" != "0" ]; then
    if ! command -v gzip > /dev/null; then
        echo "gzip is required for STATICBRAINZ_PRECOMPRESS=1"
        exit 1
    fi

    find "$STATICBRAINZ_SOURCE_DIR" -type f \
        \( -name '*.css' \
        -o -name '*.js' \
        -o -name '*.json' \
        -o -name '*.map' \
        -o -name '*.svg' \
        -o -name '*.txt' \
        -o -name '*.webmanifest' \) \
        -exec gzip -9 --keep --force {} \;
fi

for server in $STATICBRAINZ_SERVERS; do
    host=${server%%:*}
    port=${server##*:}

    if [ "$host" = "$port" ]; then
        echo "Invalid StaticBrainz server '$server'; expected host:port"
        exit 1
    fi

    retry rsync \
        $STATICBRAINZ_RSYNC_OPTIONS \
        --rsh "ssh -i $RSYNC_STATICBRAINZ_KEY -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p $port" \
        --verbose \
        "$STATICBRAINZ_SOURCE_DIR/" \
        brainz@"$host":"$STATICBRAINZ_DESTINATION_DIR"
done
