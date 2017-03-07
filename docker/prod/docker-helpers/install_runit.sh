#!/bin/sh

# This script installs runit and runsvinit (for use as the ENTRYPOINT)
# inside a container.

set -e
cd /root

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    runit

# Install go
GO_RELEASE=go1.7.linux-amd64.tar.gz
curl -O https://storage.googleapis.com/golang/$GO_RELEASE
tar xvf $GO_RELEASE
chown -R root:root go
mv go /usr/local/

# Install runsvinit
export GOPATH=/root/go
mkdir -p $GOPATH
/usr/local/go/bin/go get -u github.com/peterbourgon/runsvinit
cp $GOPATH/bin/runsvinit /usr/local/bin/

# Cleanup
rm -rf \
    $GO_RELEASE \
    $GOPATH \
    /usr/local/go \
    /var/lib/apt/lists/*
