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
