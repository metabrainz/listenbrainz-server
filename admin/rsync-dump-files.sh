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

if [ $DUMP_TYPE == "full" ]; then
    SOURCE_DIR=$RSYNC_FULLEXPORT_DIR
    SSH_KEY=$RSYNC_FULLEXPORT_KEY
elif [ $DUMP_TYPE == "incremental" ]; then
    SOURCE_DIR=$RSYNC_INCREMENTAL_DIR
    SSH_KEY=$RSYNC_INCREMENTAL_KEY
elif [ $DUMP_TYPE == "feedback" ]; then
    SOURCE_DIR=$RSYNC_SPARK_DIR
    SSH_KEY=$RSYNC_SPARK_KEY
elif [ $DUMP_TYPE == "mbcanonical" ]; then
    SOURCE_DIR=$RSYNC_MBCANONICAL_DIR
    SSH_KEY=$RSYNC_MBCANONICAL_KEY
else
    echo "Could not determine which directory (full, incremental, feedback, mbcanonical) to copy over, exiting!"
    exit 1
fi

retry rsync \
    --archive \
    --delete \
    -FF \
    --rsh "ssh -i $SSH_KEY -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p $RSYNC_FULLEXPORT_PORT" \
    --verbose \
    $SOURCE_DIR/ \
    brainz@$RSYNC_FULLEXPORT_HOST:./
