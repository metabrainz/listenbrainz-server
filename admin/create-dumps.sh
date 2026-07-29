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
# the first argument to this script is the dump type, it can be either
# full, db, incremental or feedback. the remaining arguments are forwarded
# the python dump_manager script. this can be useful in scenarios where
# we want to pass in the --dump-id manually for recreating a failed dump.

set -e

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT" || exit 1

source "admin/config.sh"
source "admin/functions.sh"

# These variables contain the names of directories that are deleted when the script
# exits, so we sanitise them here in case they were included in the environment.
DUMP_INTERMEDIATE_DIR=""
PRIVATE_DUMP_INTERMEDIATE_DIR=""

if [ "$DEPLOY_ENV" == "prod" ] && \
   { [ "$CONTAINER_NAME" == "listenbrainz-cron-prod" ] || [ "$CONTAINER_NAME" == "listenbrainz-full-dumps-cron-prod" ]; }
then
    echo "Running in $CONTAINER_NAME container, good!"
else
    echo "This container is not the production cron container, exiting..."
    exit
fi

function add_rsync_include_rule {
    RULE_FILE=$1/.rsync-filter
    FILE_NAME=$2
    MAIN_FILE_RULE="include $FILE_NAME"
    echo "$MAIN_FILE_RULE" >> "$RULE_FILE"

    MD5_FILE_RULE="include $FILE_NAME.md5"
    echo "$MD5_FILE_RULE" >> "$RULE_FILE"

    SHA256_FILE_RULE="include $FILE_NAME.sha256"
    echo "$SHA256_FILE_RULE" >> "$RULE_FILE"
}

# all cleanup code should be placed within this function
function on_exit {
    echo "Disk space when create-dumps ends:"; df -m

    if [ -n "$DUMP_INTERMEDIATE_DIR" ]; then
        rm -rf "$DUMP_INTERMEDIATE_DIR"
    fi

    if [ -n "$PRIVATE_DUMP_INTERMEDIATE_DIR" ]; then
        rm -rf "$PRIVATE_DUMP_INTERMEDIATE_DIR"
    fi

    if [ -n "$START_TIME" ]; then
        local duration=$(( $(date +%s) - START_TIME ))
        echo "create-dumps took ${duration}s to run"
    fi

    # Remove the cron lock
    /usr/local/bin/python admin/cron_lock.py unlock-cron "create-$DUMP_TYPE-dumps"
}

START_TIME=$(date +%s)
echo "This script is being run by the following user: "; whoami
echo "Disk space when create-dumps starts:" ; df -m

if [ -z $DUMP_BASE_DIR ]; then
    echo "DUMP_BASE_DIR isn't set"
    exit 1
fi

if [ -z $PRIVATE_DUMP_BASE_DIR ]; then
    echo "PRIVATE_DUMP_BASE_DIR isn't set"
    exit 1
fi

DUMP_TYPE="${1:-full}"
# consume dump type argument so that we can pass the remaining arguments to
# the python dump manager script
shift

if [ "$DUMP_TYPE" == "full" ]; then
    SUB_DIR="fullexport"
elif [ "$DUMP_TYPE" == "db" ]; then
    # database dumps are published alongside the full listen dumps
    SUB_DIR="fullexport"
elif [ "$DUMP_TYPE" == "incremental" ]; then
    SUB_DIR="incremental"
elif [ "$DUMP_TYPE" == "feedback" ]; then
    SUB_DIR="spark"
elif [ "$DUMP_TYPE" == "mbcanonical" ]; then
    SUB_DIR="mbcanonical"
elif [ "$DUMP_TYPE" == "sample" ]; then
    SUB_DIR="sample"
else
    echo "ERROR: Dump Type $DUMP_TYPE is invalid. Dump type must be one of 'full', 'db', 'incremental', 'feedback', 'mbcanonical' or 'sample'"
    exit
fi

# Lock cron, so it cannot be accidentally terminated.
/usr/local/bin/python admin/cron_lock.py lock-cron "create-$DUMP_TYPE-dumps" "Creating $DUMP_TYPE dump."

# Trap should not be called before we lock cron to avoid wiping out an existing lock file
trap on_exit EXIT

DUMP_INTERMEDIATE_DIR="$DUMP_BASE_DIR/$SUB_DIR.$$"
echo "DUMP_BASE_DIR is $DUMP_BASE_DIR"
echo "creating DUMP_INTERMEDIATE_DIR $DUMP_INTERMEDIATE_DIR"
mkdir -p "$DUMP_INTERMEDIATE_DIR"

DUMP_TEMP_DIR="$DUMP_BASE_DIR"

# only the db dumps create private dumps
if [ "$DUMP_TYPE" == "db" ]; then
    PRIVATE_DUMP_INTERMEDIATE_DIR="$PRIVATE_DUMP_BASE_DIR/$SUB_DIR.$$"
    echo "PRIVATE_DUMP_BASE_DIR is $PRIVATE_DUMP_BASE_DIR"
    echo "creating PRIVATE_DUMP_INTERMEDIATE_DIR $PRIVATE_DUMP_INTERMEDIATE_DIR"
    mkdir -p "$PRIVATE_DUMP_INTERMEDIATE_DIR"

    PRIVATE_DUMP_TEMP_DIR="$PRIVATE_DUMP_BASE_DIR"
fi

if [ "$DUMP_TYPE" == "full" ]; then
    if ! /usr/local/bin/python manage.py dump create_full -l "$DUMP_INTERMEDIATE_DIR" -lt "$DUMP_TEMP_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Full dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "db" ]; then
    if ! /usr/local/bin/python manage.py dump create_db_dump -l "$DUMP_INTERMEDIATE_DIR" -lp "$PRIVATE_DUMP_INTERMEDIATE_DIR" -lt "$DUMP_TEMP_DIR" -lpt "$PRIVATE_DUMP_TEMP_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Database dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "incremental" ]; then
    if ! /usr/local/bin/python manage.py dump create_incremental -l "$DUMP_INTERMEDIATE_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Incremental dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "feedback" ]; then
    if ! /usr/local/bin/python manage.py dump create_feedback -l "$DUMP_INTERMEDIATE_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Feedback dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "mbcanonical" ]; then
    if ! /usr/local/bin/python manage.py dump create_mbcanonical -l "$DUMP_INTERMEDIATE_DIR" "$@"; then
        echo "MB Canonical dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "sample" ]; then
    if ! /usr/local/bin/python manage.py dump create_sample -l "$DUMP_INTERMEDIATE_DIR" "$@"; then
        echo "Sample dump failed, exiting!"
        exit 1
    fi
else
    echo "Not sure what type of dump to create, exiting!"
    exit 1
fi

DUMP_ID_FILE=$(find "$DUMP_INTERMEDIATE_DIR" -type f -name 'DUMP_ID.txt')
if [ -z "$DUMP_ID_FILE" ]; then
    echo "DUMP_ID.txt not found, exiting."
    exit 1
fi

HAS_EMPTY_DIRS_OR_FILES=$(find "$DUMP_INTERMEDIATE_DIR" -empty)
if [ -n "$HAS_EMPTY_DIRS_OR_FILES" ]; then
    echo "Empty files or dirs found, exiting."
    echo "$HAS_EMPTY_DIRS_OR_FILES"
    exit 1
fi

read -r DUMP_TIMESTAMP DUMP_ID DUMP_TYPE < "$DUMP_ID_FILE"

echo "Dump created with timestamp $DUMP_TIMESTAMP"
DUMP_DIR=$(dirname "$DUMP_ID_FILE")
DUMP_NAME=$(basename "$DUMP_DIR")

# Full listen dumps are already published to the remote FTP server and are too
# large to keep a second public copy on the backup volume. Other dump types,
# including the db dumps, retain their existing local backup.
if [ "$DUMP_TYPE" != "full" ]; then
    echo "Creating Backup directories..."
    mkdir -m "$BACKUP_DIR_MODE" -p \
        "$BACKUP_DIR/$SUB_DIR" \
        "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME"
    echo "Backup directories created!"

    echo "Begin copying dumps to backup directory..."
    retry rsync -a "$DUMP_DIR/" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"
    chmod "$BACKUP_FILE_MODE" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"*
    echo "Dumps copied to backup directory!"
else
    echo "Skipping the redundant public full dump backup."
fi

if [ -n "$PRIVATE_DUMP_INTERMEDIATE_DIR" ]; then
    HAS_EMPTY_PRIVATE_DIRS_OR_FILES=$(find "$PRIVATE_DUMP_INTERMEDIATE_DIR" -empty)
    if [ -n "$HAS_EMPTY_PRIVATE_DIRS_OR_FILES" ]; then
        echo "Empty private files or dirs found, exiting."
        echo "$HAS_EMPTY_PRIVATE_DIRS_OR_FILES"
        exit 1
    fi

    PRIVATE_DUMP_ID_FILE=$(find "$PRIVATE_DUMP_INTERMEDIATE_DIR" -type f -name 'DUMP_ID.txt')
    if [ -z "$PRIVATE_DUMP_ID_FILE" ]; then
        echo "DUMP_ID.txt not found, exiting."
        exit 1
    fi

    read -r PRIVATE_DUMP_TIMESTAMP PRIVATE_DUMP_ID PRIVATE_DUMP_TYPE < "$PRIVATE_DUMP_ID_FILE"
    echo "Dump created with timestamp $PRIVATE_DUMP_TIMESTAMP"
    PRIVATE_DUMP_DIR=$(dirname "$PRIVATE_DUMP_ID_FILE")
    PRIVATE_DUMP_NAME=$(basename "$PRIVATE_DUMP_DIR")

    # Backup dumps to the backup volume
    echo "Creating private dumps backup directories..."
    mkdir -m "$BACKUP_FILE_MODE" -p \
        "$PRIVATE_BACKUP_DIR/$SUB_DIR" \
        "$PRIVATE_BACKUP_DIR/$SUB_DIR/$PRIVATE_DUMP_NAME"
    echo "Private dumps backup directories created!"

    # Copy the files into the backup directory
    echo "Begin copying private dumps to private backup directory..."
    retry rsync -a "$PRIVATE_DUMP_DIR/" "$PRIVATE_BACKUP_DIR/$SUB_DIR/$PRIVATE_DUMP_NAME/"
    chmod "$BACKUP_FILE_MODE" "$PRIVATE_BACKUP_DIR/$SUB_DIR/$PRIVATE_DUMP_NAME/"*
    echo "Dumps copied to backup directory!"
fi

# rsync the files into the FTP server
FTP_CURRENT_DUMP_DIR="$FTP_DIR/$SUB_DIR/$DUMP_NAME"

# create the dir in which to copy the dumps before
# changing their permissions to the FTP_FILE_MODE
echo "Creating FTP directories..."
mkdir  -m "$FTP_DIR_MODE" -p \
    "$FTP_DIR/$SUB_DIR" \
    "$FTP_CURRENT_DUMP_DIR"

# Make sure all dump files are owned by the correct user and set appropriate
# mode for files to be uploaded to the FTP server. Move full-dump files into
# staging instead of retaining another complete copy in the working directory.
if [ "$DUMP_TYPE" == "full" ]; then
    retry rsync -a --remove-source-files "$DUMP_DIR/" "$FTP_CURRENT_DUMP_DIR/"
    rm -rf -- "$DUMP_DIR"
else
    retry rsync -a "$DUMP_DIR/" "$FTP_CURRENT_DUMP_DIR/"
fi
echo "Fixing FTP permissions"
chmod "$FTP_DIR_MODE" "$FTP_CURRENT_DUMP_DIR"
chmod "$FTP_FILE_MODE" "$FTP_CURRENT_DUMP_DIR/"*

# Create a fresh rsync filter for this dump. A directory reused after a retry
# may contain a retention-marker filter, which must not hide the new payload.
rm -f -- "$FTP_CURRENT_DUMP_DIR/.ftp-retention-marker"
: > "$FTP_CURRENT_DUMP_DIR/.rsync-filter"

add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-public-dump-$DUMP_TIMESTAMP.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-public-timescale-dump-$DUMP_TIMESTAMP.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-listens-dump-$DUMP_ID-$DUMP_TIMESTAMP-$DUMP_TYPE.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-spark-dump-$DUMP_ID-$DUMP_TIMESTAMP-$DUMP_TYPE.tar"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-feedback-dump-$DUMP_TIMESTAMP.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-statistics-dump-$DUMP_TIMESTAMP.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-sample-dump-$DUMP_TIMESTAMP.tar.zst"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "musicbrainz-canonical-dump-$DUMP_TIMESTAMP.tar.zst"

EXCLUDE_RULE="exclude *"
echo "$EXCLUDE_RULE" >> "$FTP_CURRENT_DUMP_DIR/.rsync-filter"
cat "$FTP_CURRENT_DUMP_DIR/.rsync-filter"


if [ "$DUMP_TYPE" == "full" ]; then
    # Full listen dump FTP retention is applied by rsync-dump-files.sh only after
    # every pending payload has uploaded successfully. Remove public full dumps
    # left on the legacy backup volume now that it is no longer used for them.
    /usr/local/bin/python manage.py dump delete_old_dumps \
        --remove-all-full-dumps \
        "$BACKUP_DIR/$SUB_DIR"
elif [ "$DUMP_TYPE" == "db" ]; then
    # The FTP and backup fullexport directories also contain full dumps. A db
    # run must not expire full payloads which may still be pending upload.
    /usr/local/bin/python manage.py dump delete_old_dumps \
        --only-db-dumps \
        "$FTP_DIR/$SUB_DIR"
    /usr/local/bin/python manage.py dump delete_old_dumps \
        --only-db-dumps \
        "$BACKUP_DIR/$SUB_DIR"
else
    /usr/local/bin/python manage.py dump delete_old_dumps "$FTP_DIR/$SUB_DIR"
    /usr/local/bin/python manage.py dump delete_old_dumps "$BACKUP_DIR/$SUB_DIR"
fi
if [ "$DUMP_TYPE" == "db" ]; then
    /usr/local/bin/python manage.py dump delete_old_dumps \
        --only-db-dumps \
        "$PRIVATE_BACKUP_DIR/$SUB_DIR"
else
    /usr/local/bin/python manage.py dump delete_old_dumps "$PRIVATE_BACKUP_DIR/$SUB_DIR"
fi

# rsync to ftp folder taking care of the rules
./admin/rsync-dump-files.sh "$DUMP_TYPE" "$DUMP_NAME"

echo "Dumps created and uploaded to the FTP server; applicable backups completed!"
