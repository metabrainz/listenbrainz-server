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

set -e

LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT" || exit 1

source "admin/config.sh"
source "admin/functions.sh"

# This variable contains the name of a directory that is deleted when the script
# exits, so we sanitise it here in case it was included in the environment.
TMPDIR=""

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

    if [ -n "$TMPDIR" ]; then
        rm -rf "$TMPDIR"
    fi

    if [ -n "$START_TIME" ]; then
        local duration=$(( $(date +%s) - START_TIME ))
        echo "create-dumps took ${duration}s to run"
    fi
}

trap on_exit EXIT

START_TIME=$(date +%s)
echo "This script is being run by the following user: "; whoami
echo "Disk space when create-dumps starts:" ; df -m


DUMP_TYPE="${1:-full}"

if [ "$DUMP_TYPE" == "full" ]; then
    SUB_DIR="fullexport"
elif [ "$DUMP_TYPE" == "incremental" ]; then
    SUB_DIR="incremental"
elif [ "$DUMP_TYPE" == "feedback" ]; then
    SUB_DIR="spark"
else
    echo "Dump type must be one of 'full', 'incremental' or 'feedback'"
    exit
fi

TMPDIR=$(mktemp --tmpdir="$TEMP_DIR" -d -t "$SUB_DIR.XXXXXXXXXX")

if [ "$DUMP_TYPE" == "full" ]; then
    if ! /usr/local/bin/python manage.py dump create_full -l "$TMPDIR" -t "$DUMP_THREADS" --last-dump-id; then
        echo "Full dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "incremental" ]; then
    if ! /usr/local/bin/python manage.py dump create_incremental -l "$TMPDIR" -t "$DUMP_THREADS"; then
        echo "Incremental dump failed, exiting!"
        exit 1
    fi
elif [ "$DUMP_TYPE" == "feedback" ]; then
    if ! /usr/local/bin/python manage.py dump create_feedback -l "$TMPDIR" -t "$DUMP_THREADS"; then
        echo "Feedback dump failed, exiting!"
        exit 1
    fi
else
    echo "Not sure what type of dump to create, exiting!"
    exit 1
fi

DUMP_ID_FILE=$(find "$TMPDIR" -type f -name 'DUMP_ID.txt')
if [ -z "$DUMP_ID_FILE" ]; then
    echo "DUMP_ID.txt not found, exiting."
    exit 1
fi

HAS_EMPTY_DIRS_OR_FILES=$(find "$TMPDIR" -empty)
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
# Create backup directories owned by user "listenbrainz"
echo "Creating Backup directories..."
mkdir -m "$BACKUP_DIR_MODE" -p \
         "$BACKUP_DIR/$SUB_DIR/" \
         "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME"
chown "$BACKUP_USER:$BACKUP_GROUP" \
      "$BACKUP_DIR/$SUB_DIR/" \
      "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME"
echo "Backup directories created!"

# Copy the files into the backup directory
echo "Begin copying dumps to backup directory..."
retry rsync -a "$DUMP_DIR/" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"
chmod "$BACKUP_FILE_MODE" "$BACKUP_DIR/$SUB_DIR/$DUMP_NAME/"*
echo "Dumps copied to backup directory!"


# rsync the files into the FTP server
FTP_CURRENT_DUMP_DIR="$FTP_DIR/$SUB_DIR/$DUMP_NAME"

# create the dir in which to copy the dumps before
# changing their permissions to the FTP_FILE_MODE
echo "Creating FTP directories and setting permissions..."
mkdir -m "$FTP_DIR_MODE" -p "$FTP_CURRENT_DUMP_DIR"

# make sure these dirs are owned by the correct user
chown "$FTP_USER:$FTP_GROUP" \
      "$FTP_DIR" \
      "$FTP_DIR/$SUB_DIR" \
      "$FTP_CURRENT_DUMP_DIR"

# make sure all dump files are owned by the correct user
# and set appropriate mode for files to be uploaded to
# the FTP server
retry rsync -a "$DUMP_DIR/" "$FTP_CURRENT_DUMP_DIR/"
chmod "$FTP_FILE_MODE" "$FTP_CURRENT_DUMP_DIR/"*

# create an explicit rsync filter for the new private dump in the
# ftp folder
touch "$FTP_CURRENT_DUMP_DIR/.rsync-filter"

add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-public-dump-$DUMP_TIMESTAMP.tar.xz"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-listens-dump-$DUMP_ID-$DUMP_TIMESTAMP-$DUMP_TYPE.tar.xz"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-listens-dump-$DUMP_ID-$DUMP_TIMESTAMP-spark-$DUMP_TYPE.tar.xz"
add_rsync_include_rule \
    "$FTP_CURRENT_DUMP_DIR" \
    "listenbrainz-feedback-dump-$DUMP_TIMESTAMP.tar.xz"

EXCLUDE_RULE="exclude *"
echo "$EXCLUDE_RULE" >> "$FTP_CURRENT_DUMP_DIR/.rsync-filter"
cat "$FTP_CURRENT_DUMP_DIR/.rsync-filter"


/usr/local/bin/python manage.py dump delete_old_dumps "$FTP_DIR/$SUB_DIR"
/usr/local/bin/python manage.py dump delete_old_dumps "$BACKUP_DIR/$SUB_DIR"
/usr/local/bin/python manage.py dump delete_old_dumps "$TEMP_DIR/$SUB_DIR"

# rsync to ftp folder taking care of the rules
./admin/rsync-dump-files.sh "$DUMP_TYPE"

echo "Dumps created, backed up and uploaded to the FTP server!"
