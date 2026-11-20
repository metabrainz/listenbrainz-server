#!/bin/sh
# Start a single node Garage cluster and provision the development access key and
# buckets. Garage needs a layout to be assigned and applied before it accepts any
# S3 request so this cannot be done from a plain `garage server` invocation.
set -e

# the healthcheck waits for this file, drop any copy left behind by a previous run of the
# container so that a restart is only reported healthy once it has provisioned itself again
rm -f /tmp/garage-provisioned

garage server &
server_pid=$!

echo "Waiting for garage to start up..."
until garage status > /dev/null 2>&1; do
    if ! kill -0 "$server_pid" 2> /dev/null; then
        echo "garage server exited during startup"
        exit 1
    fi
    sleep 1
done

# the layout can only be assigned and applied once, the sentinel lives on the data volume
# so that it survives a restart of the container
if [ ! -f /var/lib/garage/meta/.provisioned ]; then
    node_id=$(garage node id -q | cut -d@ -f1)
    echo "Assigning layout to node $node_id"
    garage layout assign -z dc1 -c 1G "$node_id"
    garage layout apply --version 1

    echo "Importing development access key"
    garage key import --yes -n listenbrainz "$GARAGE_ACCESS_KEY" "$GARAGE_SECRET_KEY"
    garage key allow --create-bucket "$GARAGE_ACCESS_KEY"

    touch /var/lib/garage/meta/.provisioned
fi

# creating buckets is idempotent and runs on every start so that buckets added to
# GARAGE_BUCKETS later are created on an already provisioned volume too
for bucket in $GARAGE_BUCKETS; do
    if garage bucket info "$bucket" > /dev/null 2>&1; then
        echo "Bucket $bucket already exists"
    else
        echo "Creating bucket $bucket"
        garage bucket create "$bucket"
    fi
    garage bucket allow --read --write --owner "$bucket" --key "$GARAGE_ACCESS_KEY"
done

# the S3 api port is open long before the layout is applied and the buckets exist, so the
# healthcheck waits for this instead of the port
touch /tmp/garage-provisioned

echo "Garage is ready."
wait "$server_pid"
