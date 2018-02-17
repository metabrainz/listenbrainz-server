#!/bin/bash

DUMP_THREADS=4

# Where to back things up to, who should own the backup files, and what mode
# those files should have.
# The backups include a full database export, and all replication data.
BACKUP_DIR=/home/listenbrainz/backup
BACKUP_USER=listenbrainz
BACKUP_GROUP=listenbrainz
BACKUP_DIR_MODE=700
BACKUP_FILE_MODE=600

# Where to put database exports, for public consumption;
# who should own them, and what mode they should have.
FTP_DATA_DIR=/var/ftp/pub/musicbrainz/listenbrainz
FTP_USER=musicbrainz
FTP_GROUP=musicbrainz
FTP_DIR_MODE=755
FTP_FILE_MODE=644

RSYNC_FULLEXPORT_HOST='10.2.2.28'
RSYNC_FULLEXPORT_PORT='65415'
RSYNC_FULLEXPORT_DIR="$FTP_DATA_DIR/fullexport"
RSYNC_FULLEXPORT_KEY='~/.ssh/rsync-listenbrainz-dumps-full'
