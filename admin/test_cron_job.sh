#!/bin/bash

echo "$(date): Start"
sleep 60

echo "$(date): Sourced"
source /code/listenbrainz/admin/config.sh

echo "$(date): Locking Cron"
/usr/local/bin/python /code/listenbrainz/admin/cron_lock.py lock-cron test-locks "Testing cron_lock script"

echo "$(date): Sleeping"
sleep 300

echo "$(date): Unlocking Cron"
/usr/local/bin/python /code/listenbrainz/admin/cron_lock.py unlock-cron test-locks
echo "$(date): Exit"
