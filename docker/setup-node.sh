#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Usage: setup-node.sh <master ip> <swarm token>"
    exit
fi

MASTER_IP=$1
SWARM_TOKEN=$2

# Install docker, the MetaBrainz way
apt-get update
apt-get -y install \
    apt-transport-https

git clone https://github.com/metabrainz/docker-helpers.git
cd docker-helpers
./docker_install_xenial.sh

docker swarm join --token $SWARM_TOKEN $MASTER_IP:2377

reboot
