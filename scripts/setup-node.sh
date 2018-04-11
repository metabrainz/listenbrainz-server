#!/bin/sh

CONSUL_IMAGE=library/consul:0.9.3

source "${BASH_SOURCE%/*}/consul.sh"

apt-get update
apt-get -y install \
    apt-transport-https

git clone https://github.com/metabrainz/docker-helpers.git
cd docker-helpers
./docker_install_xenial.sh

docker pull metabrainz/spark-worker

docker run \
   --name spark-worker \
   --restart=unless-stopped \
   -d \
   metabrainz/spark-worker

start_consul_agent
start_registrator
