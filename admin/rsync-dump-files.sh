#!/bin/bash

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2018 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

unset SSH_AUTH_SOCK

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT"

source admin/config.sh
source admin/functions.sh

DUMP_TYPE=$1
DUMP_NAME=$2
DESTINATION="brainz@$RSYNC_FULLEXPORT_HOST:./"
RSYNC_FILTER_OPTIONS=(-FF)
RSYNC_DELETE_OPTIONS=(--delete)

function build_rsync_filter_options {
    RSYNC_FILTER_OPTIONS=(-FF)

    # Only the fullexport dir contains full listen dump marker directories.
    if [ "$DUMP_TYPE" != "full" ] && [ "$DUMP_TYPE" != "db" ]; then
        return
    fi

    # Command-line protect rules are passed to the receiving rsync process.
    # They preserve payloads for retained marker directories while
    # --delete/--delete-after removes remote directories whose local markers
    # expired. The db dump sync uses the same rules so that it never deletes
    # the full listen dump payloads it has no local copy of.
    shopt -s nullglob
    for RETAINED_DUMP_DIR in "$SOURCE_DIR"/listenbrainz-dump-*-full; do
        RETAINED_DUMP_NAME=$(basename "$RETAINED_DUMP_DIR")
        if [ -f "$RETAINED_DUMP_DIR/.ftp-retention-marker" ] && \
           [[ "$RETAINED_DUMP_NAME" =~ ^listenbrainz-dump-[0-9]+-[0-9]{8}-[0-9]{6}-full$ ]]
        then
            RSYNC_FILTER_OPTIONS+=(--filter="protect /$RETAINED_DUMP_NAME/***")
        fi
    done
    shopt -u nullglob
}

function sync_source {
    build_rsync_filter_options
    retry rsync \
        --archive \
        "${RSYNC_DELETE_OPTIONS[@]}" \
        "${RSYNC_FILTER_OPTIONS[@]}" \
        --rsh "ssh -i $SSH_KEY -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p $RSYNC_FULLEXPORT_PORT" \
        --verbose \
        "$SOURCE_DIR/" \
        "$DESTINATION"
}

if [ "$DUMP_TYPE" == "full" ]; then
    if [[ ! "$DUMP_NAME" =~ ^listenbrainz-dump-[0-9]+-[0-9]{8}-[0-9]{6}-full$ ]]; then
        echo "Invalid or missing full dump name '$DUMP_NAME', exiting!"
        exit 1
    fi
    # Full dump directories without payloads are retained locally as markers.
    # Mirroring the parent directory lets --delete enforce the FTP retention
    # constant without retaining the large dump files locally.
    SOURCE_DIR=$RSYNC_FULLEXPORT_DIR
    SSH_KEY=$RSYNC_FULLEXPORT_KEY
    # Expire old remote dumps only after the new payload transfer succeeds.
    RSYNC_DELETE_OPTIONS=(--delete-after)
    if [ ! -d "$SOURCE_DIR/$DUMP_NAME" ]; then
        echo "Full dump source directory '$SOURCE_DIR/$DUMP_NAME' does not exist, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "db" ]; then
    # Database dumps are published alongside the full listen dumps and use the
    # same rsync credentials, but their payloads are small enough to be retained
    # locally, like incremental dumps.
    SOURCE_DIR=$RSYNC_FULLEXPORT_DIR
    SSH_KEY=$RSYNC_FULLEXPORT_KEY
elif [ "$DUMP_TYPE" == "incremental" ]; then
    SOURCE_DIR=$RSYNC_INCREMENTAL_DIR
    SSH_KEY=$RSYNC_INCREMENTAL_KEY
elif [ "$DUMP_TYPE" == "feedback" ]; then
    SOURCE_DIR=$RSYNC_SPARK_DIR
    SSH_KEY=$RSYNC_SPARK_KEY
elif [ "$DUMP_TYPE" == "mbcanonical" ]; then
    SOURCE_DIR=$RSYNC_MBCANONICAL_DIR
    SSH_KEY=$RSYNC_MBCANONICAL_KEY
elif [ "$DUMP_TYPE" == "sample" ]; then
    SOURCE_DIR=$RSYNC_SAMPLE_DIR
    SSH_KEY=$RSYNC_SAMPLE_KEY
else
    echo "Could not determine which directory (full, db, incremental, feedback, mbcanonical, sample) to copy over, exiting!"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Dump source directory '$SOURCE_DIR' does not exist, exiting!"
    exit 1
fi

if ! sync_source; then
    echo "Failed to upload $DUMP_TYPE dump; local files have been preserved."
    exit 1
fi

if [ "$DUMP_TYPE" == "full" ]; then
    # Keep only tiny directory/filter markers after a successful transfer. The
    # exclude rule protects retained remote payloads from deletion on the next
    # run, while removal of older marker directories allows rsync to expire the
    # corresponding remote dumps.
    shopt -s nullglob
    for LOCAL_DUMP_DIR in "$SOURCE_DIR"/listenbrainz-dump-*-full; do
        LOCAL_DUMP_NAME=$(basename "$LOCAL_DUMP_DIR")
        if [ ! -d "$LOCAL_DUMP_DIR" ] || [ -L "$LOCAL_DUMP_DIR" ] || \
           [[ ! "$LOCAL_DUMP_NAME" =~ ^listenbrainz-dump-[0-9]+-[0-9]{8}-[0-9]{6}-full$ ]]
        then
            echo "Ignoring unexpected directory '$LOCAL_DUMP_DIR' during local cleanup."
            continue
        fi

        find "$LOCAL_DUMP_DIR" -mindepth 1 -delete
        touch "$LOCAL_DUMP_DIR/.ftp-retention-marker"
        printf 'exclude *\n' > "$LOCAL_DUMP_DIR/.rsync-filter"
    done
    shopt -u nullglob

    # Every payload is now safe on the remote host, so it is safe to expire
    # markers beyond the retention constant. A second metadata-only
    # rsync applies those expirations remotely.
    if ! /usr/local/bin/python manage.py dump delete_old_dumps "$SOURCE_DIR"
    then
        echo "Full dumps uploaded, but local retention-marker cleanup failed."
        exit 1
    fi

    if ! sync_source; then
        echo "Full dumps uploaded, but remote retention cleanup failed."
        exit 1
    fi

    echo "Full dumps uploaded successfully; local payloads removed and FTP retention applied."
fi
