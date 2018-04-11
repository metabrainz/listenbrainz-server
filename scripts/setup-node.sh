#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "  Usage: start-node.sh <private subnet>"
fi

PRIVATE_SUBNET=$1

PRIVATE_IP=$(ip -4 route get $PRIVATE_SUBNET|awk '{print $NF;exit}')
CONSUL_IMAGE=library/consul:0.9.3

source "${BASH_SOURCE%/*}/consul.sh"

# Install docker, the MetaBrainz way
apt-get update
apt-get -y install \
    apt-transport-https

git clone https://github.com/metabrainz/docker-helpers.git
cd docker-helpers
./docker_install_xenial.sh

# start the consul agent and registrator
start_consul_agent
start_registrator

# start the spark worker container
docker pull metabrainz/spark-worker
docker run \
   --name spark-worker \
   --restart=unless-stopped \
   -d \
   metabrainz/spark-worker
