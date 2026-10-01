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

# usage
#   rsync-dump-files.sh <dump type> <dump name> <source dir>
#
# Publishes one dump directory to the FTP host and then expires the dumps which
# have fallen outside their retention window.
#
# The remote host, not this machine, is the source of truth for what has been
# published, so nothing here mirrors a local directory. Uploading only ever adds
# the one named dump, and expiry is driven by a listing of the remote host. That
# is what lets full listen dumps be deleted locally right after upload without
# any local bookkeeping to stand in for them.
#
# Set DUMP_DRY_RUN=1 to log the remote deletions without performing them.

unset SSH_AUTH_SOCK

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT" || exit 1

source admin/config.sh
source admin/functions.sh

DUMP_TYPE=$1
DUMP_NAME=$2
SOURCE_DIR=$3

# Names are interpolated into remote paths that get deleted, so only well-formed
# dump directory names are accepted. Must be kept in step with the DUMP_KINDS
# table in listenbrainz/dumps/cleanup.py.
DUMP_NAME_PATTERN='^(listenbrainz-dump-[0-9]+-[0-9]{8}-[0-9]{6}-(full|db|incremental)'
DUMP_NAME_PATTERN+='|listenbrainz-(feedback|sample)-[0-9]{8}-[0-9]{6}-full'
DUMP_NAME_PATTERN+='|musicbrainz-canonical-dump-[0-9]{8}-[0-9]{6})$'

case "$DUMP_TYPE" in
    # database dumps are published alongside the full listen dumps
    full|db)     SSH_KEY=$RSYNC_FULLEXPORT_KEY ;;
    incremental) SSH_KEY=$RSYNC_INCREMENTAL_KEY ;;
    feedback)    SSH_KEY=$RSYNC_SPARK_KEY ;;
    mbcanonical) SSH_KEY=$RSYNC_MBCANONICAL_KEY ;;
    sample)      SSH_KEY=$RSYNC_SAMPLE_KEY ;;
    *)
        echo "Dump type '$DUMP_TYPE' must be one of full, db, incremental, feedback, mbcanonical or sample, exiting!"
        exit 1
        ;;
esac

if [[ ! "$DUMP_NAME" =~ $DUMP_NAME_PATTERN ]]; then
    echo "Invalid or missing dump name '$DUMP_NAME', exiting!"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Dump source directory '$SOURCE_DIR' does not exist, exiting!"
    exit 1
fi

if [ ! -f "$SOURCE_DIR/.rsync-filter" ]; then
    echo "Rsync filter '$SOURCE_DIR/.rsync-filter' does not exist, refusing to publish!"
    exit 1
fi

DESTINATION="brainz@$RSYNC_FULLEXPORT_HOST:./"
RSYNC_RSH="ssh -i $SSH_KEY -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p $RSYNC_FULLEXPORT_PORT"

EMPTY_DIR=$(mktemp -d)
trap 'rm -rf -- "$EMPTY_DIR"' EXIT

function publish_dump {
    retry rsync \
        --archive \
        --verbose \
        -FF \
        --rsh "$RSYNC_RSH" \
        "$SOURCE_DIR/" \
        "$DESTINATION$DUMP_NAME/"
}

# Print the name of every directory published on the remote host.
function list_remote_dumps {
    rsync --list-only --rsh "$RSYNC_RSH" "$DESTINATION" | awk '/^d/ && $5 != "." { print $5 }'
}

# Delete one published dump from the remote host. The include rules name the
# single directory to remove and everything else is excluded, which protects it
# from --delete; the source is an empty directory, so nothing is transferred.
function expire_remote_dump {
    local dump_name=$1
    local dry_run_option=()

    if [ -n "$DUMP_DRY_RUN" ]; then
        dry_run_option=(--dry-run)
        echo "Dry run: would remove '$dump_name' from the FTP server."
    else
        echo "Removing '$dump_name' from the FTP server..."
    fi

    retry rsync \
        --recursive \
        --delete \
        --verbose \
        "${dry_run_option[@]}" \
        --rsh "$RSYNC_RSH" \
        --include "/$dump_name" \
        --include "/$dump_name/***" \
        --exclude '*' \
        "$EMPTY_DIR/" \
        "$DESTINATION"
}

# Expire the published dumps which have fallen outside their retention window.
# The retention policy itself lives in the dump manager; this only needs to know
# how to list and how to delete.
function apply_remote_retention {
    local remote_dumps expired dump_name

    if ! remote_dumps=$(list_remote_dumps); then
        echo "Could not list the dumps on the FTP server, not expiring anything!"
        return 1
    fi

    # An empty listing means the listing failed in a way rsync did not report,
    # since the dump just uploaded should be in it. Do not act on it.
    if [ -z "$remote_dumps" ]; then
        echo "The FTP server listing is empty, not expiring anything!"
        return 1
    fi

    if ! expired=$(printf '%s\n' "$remote_dumps" | /usr/local/bin/python manage.py dump list_expired_dumps); then
        echo "Could not work out which dumps have expired, not expiring anything!"
        return 1
    fi

    if [ -z "$expired" ]; then
        echo "No dumps have expired on the FTP server."
        return 0
    fi

    while read -r dump_name; do
        if [[ ! "$dump_name" =~ $DUMP_NAME_PATTERN ]]; then
            echo "Refusing to remove unexpected remote directory '$dump_name'!"
            return 1
        fi
        if ! expire_remote_dump "$dump_name"; then
            echo "Failed to remove '$dump_name' from the FTP server!"
            return 1
        fi
    done <<< "$expired"
}

if ! publish_dump; then
    echo "Failed to upload $DUMP_TYPE dump '$DUMP_NAME'; local files have been preserved."
    exit 1
fi
echo "Uploaded $DUMP_TYPE dump '$DUMP_NAME' to the FTP server."

if ! apply_remote_retention; then
    echo "$DUMP_TYPE dump '$DUMP_NAME' was uploaded, but FTP retention failed."
    exit 1
fi

echo "$DUMP_TYPE dump '$DUMP_NAME' uploaded and FTP retention applied."
