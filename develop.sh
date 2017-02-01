#!/bin/bash

if [[ $USER == "vagrant" ]]; then
    echo "Running as a vagrant VM. DATA_DIR = /home/vagrant/data"
    export DATA_DIR=/home/vagrant/lb-docker-data
else
    echo "Running as a non-vagrant VM. DATA_DIR = ."
    export DATA_DIR=.
fi

mkdir -p $DATA_DIR

if [[ ! -d "docker" ]]; then
    echo "This script must be run from the top level directory of the listenbrainz-server source."
    exit -1
fi

# invoke docker, but ungrep noisy influx log messages that I can't turn off
docker-compose -f docker/docker-compose.prod.yml build && docker-compose -f docker/docker-compose.prod.yml up
#docker-compose -f docker/docker-compose.prod.yml build && docker-compose -f docker/docker-compose.prod.yml up | grep -v '\[cacheloader\]' | grep -v '\[store\]' | grep -v '\[shard\]'
