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

echo "This script is being run by the following user: "; whoami

# This is to help with disk space monitoring - run "df" before and after
echo "Disk space when create-dumps starts:" ; df -m
trap 'echo "Disk space when create-dumps ends:" ; df -m' 0


LB_SERVER_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)
cd "$LB_SERVER_ROOT"

source admin/config.sh
source admin/functions.sh

TEMP_DIR="/home/listenbrainz/data/dumps"

/usr/local/bin/python manage.py dump create -l $TEMP_DIR -t $DUMP_THREADS

DUMP_NAME=`ls $TEMP_DIR | sort -r | head -1`
DUMP_DIR="$TEMP_DIR"/"$DUMP_NAME"

echo "Creating Backup directories..."
mkdir -m "$BACKUP_DIR_MODE" -p \
         "$BACKUP_DIR"/fullexport/ \
         "$BACKUP_DIR"/fullexport/"$DUMP_NAME"
chown "$BACKUP_USER:$BACKUP_GROUP" \
      "$BACKUP_DIR"/fullexport/ \
      "$BACKUP_DIR"/fullexport/"$DUMP_NAME"
echo "Backup directories created!"

echo "Begin copying..."
chown "$BACKUP_USER:$BACKUP_GROUP" "$DUMP_DIR"/*
chmod "$BACKUP_FILE_MODE" "$DUMP_DIR"/*
retry cp -a "$DUMP_DIR"/* "$BACKUP_DIR"/fullexport/"$DUMP_NAME"/
echo "Dumps copied to backup directory!"
