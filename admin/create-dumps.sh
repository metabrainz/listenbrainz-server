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
# full, incremental or feedback. the remaining arguments are forwarded
# the python dump_manager script. this can be useful in scenarios where
# we want to pass in the --dump-id manually for recreating a failed dump.

set -e

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT" || exit 1

source "admin/config.sh"
source "admin/functions.sh"

# This variable contains the name of a directory that is deleted when the script
# exits, so we sanitise it here in case it was included in the environment.
DUMP_TEMP_DIR=""

if [ "$CONTAINER_NAME" == "listenbrainz-cron-prod" ] && [ "$PROD" == "prod" ]
then
    echo "Running in listenbrainz-cron-prod container, good!"
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

    if [ -n "$DUMP_TEMP_DIR" ]; then
        rm -rf "$DUMP_TEMP_DIR"
    fi

    if [ -n "$PRIVATE_DUMP_TEMP_DIR" ]; then
        rm -rf "$PRIVATE_DUMP_TEMP_DIR"
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
elif [ "$DUMP_TYPE" == "incremental" ]; then
    SUB_DIR="incremental"
elif [ "$DUMP_TYPE" == "feedback" ]; then
    SUB_DIR="spark"
elif [ "$DUMP_TYPE" == "mbcanonical" ]; then
    SUB_DIR="mbcanonical"
else
    echo "ERROR: Dump Type $DUMP_TYPE is invalid. Dump type must be one of 'full', 'incremental', 'feedback' or 'mbcanonical'"
    exit
fi

# Lock cron, so it cannot be accidentally terminated.
/usr/local/bin/python admin/cron_lock.py lock-cron "create-$DUMP_TYPE-dumps" "Creating $DUMP_TYPE dump."

# Trap should not be called before we lock cron to avoid wiping out an existing lock file
trap on_exit EXIT

DUMP_TEMP_DIR="$DUMP_BASE_DIR/$SUB_DIR.$$"
echo "DUMP_BASE_DIR is $DUMP_BASE_DIR"
echo "creating DUMP_TEMP_DIR $DUMP_TEMP_DIR"
mkdir -p "$DUMP_TEMP_DIR"

PRIVATE_DUMP_TEMP_DIR="$PRIVATE_DUMP_BASE_DIR/$SUB_DIR.$$"
echo "PRIVATE_DUMP_BASE_DIR is $PRIVATE_DUMP_BASE_DIR"
echo "creating PRIVATE_DUMP_TEMP_DIR $PRIVATE_DUMP_TEMP_DIR"
mkdir -p "$PRIVATE_DUMP_TEMP_DIR"

if [ "$DUMP_TYPE" == "full" ]; then
    if ! /usr/local/bin/python manage.py dump create_full -l "$DUMP_TEMP_DIR" -lp "$PRIVATE_DUMP_TEMP_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Full dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "incremental" ]; then
    if ! /usr/local/bin/python manage.py dump create_incremental -l "$DUMP_TEMP_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Incremental dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "feedback" ]; then
    if ! /usr/local/bin/python manage.py dump create_feedback -l "$DUMP_TEMP_DIR" -t "$DUMP_THREADS" "$@"; then
        echo "Feedback dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "mbcanonical" ]; then
    if ! /usr/local/bin/python manage.py dump create_mbcanonical -l "$DUMP_TEMP_DIR" "$@"; then
        echo "MB Canonical dump failed, exiting!"
        exit 1
    fi
else
    echo "Not sure what type of dump to create, exiting!"
    exit 1
fi

DUMP_ID_FILE=$(find "$DUMP_TEMP_DIR" -type f -name 'DUMP_ID.txt')
if [ -z "$DUMP_ID_FILE" ]; then
    echo "DUMP_ID.txt not found, exiting."
    exit 1
fi

HAS_EMPTY_DIRS_OR_FILES=$(find "$DUMP_TEMP_DIR" -empty)
if [ -n "$HAS_EMPTY_DIRS_OR_FILES" ]; then
    echo "Empty files or dirs found, exiting."
    echo "$HAS_EMPTY_DIRS_OR_FILES"
    exit 1
fi

read -r DUMP_TIMESTAMP DUMP_ID DUMP_TYPE < "$DUMP_ID_FILE"

echo "Dump created with timestamp $DUMP_TIMESTAMP"
DUMP_DIR=$(dirname "$DUMP_ID_FILE")
DUMP_NAME=$(basename "$DUMP_DIR")

# Backup dumps to the backup volume
echo "Creating Backup directories..."
mkdir -m "$BACKUP_DIR_MODE" -p \
    "$BACKUP_DIR/$SUB_DIR" \
    "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME"
echo "Backup directories created!"

# Copy the files into the backup directory
echo "Begin copying dumps to backup directory..."
retry rsync -a "$DUMP_DIR/" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"
chmod "$BACKUP_FILE_MODE" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"*
echo "Dumps copied to backup directory!"

HAS_EMPTY_PRIVATE_DIRS_OR_FILES=$(find "$PRIVATE_DUMP_TEMP_DIR" -empty)
if [ -z "$HAS_EMPTY_PRIVATE_DIRS_OR_FILES" ]; then
    # private dumps directory is not empty

    PRIVATE_DUMP_ID_FILE=$(find "$PRIVATE_DUMP_TEMP_DIR" -type f -name 'DUMP_ID.txt')
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

# make sure all dump files are owned by the correct user
# and set appropriate mode for files to be uploaded to
# the FTP server
retry rsync -a "$DUMP_DIR/" "$FTP_CURRENT_DUMP_DIR/"
echo "Fixing FTP permissions"
chmod "$FTP_DIR_MODE" "$FTP_CURRENT_DUMP_DIR"
chmod "$FTP_FILE_MODE" "$FTP_CURRENT_DUMP_DIR/"*

# create an explicit rsync filter for the new private dump in the
# ftp folder
touch "$FTP_CURRENT_DUMP_DIR/.rsync-filter"

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
    "musicbrainz-canonical-dump-$DUMP_TIMESTAMP.tar.zst"

EXCLUDE_RULE="exclude *"
echo "$EXCLUDE_RULE" >> "$FTP_CURRENT_DUMP_DIR/.rsync-filter"
cat "$FTP_CURRENT_DUMP_DIR/.rsync-filter"


/usr/local/bin/python manage.py dump delete_old_dumps "$FTP_DIR/$SUB_DIR"
/usr/local/bin/python manage.py dump delete_old_dumps "$BACKUP_DIR/$SUB_DIR"
/usr/local/bin/python manage.py dump delete_old_dumps "$PRIVATE_BACKUP_DIR/$SUB_DIR"

# rsync to ftp folder taking care of the rules
./admin/rsync-dump-files.sh "$DUMP_TYPE"

echo "Dumps created, backed up and uploaded to the FTP server!"
