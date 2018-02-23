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

retry rsync \
    --archive \
    --delete \
    -FF \
    --rsh "ssh -i $RSYNC_FULLEXPORT_KEY -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -p $RSYNC_FULLEXPORT_PORT" \
    --verbose \
    $RSYNC_FULLEXPORT_DIR/ \
    brainz@$RSYNC_FULLEXPORT_HOST:./
