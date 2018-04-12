#!/bin/sh

# Install docker, the MetaBrainz way
apt-get update
apt-get -y install \
    apt-transport-https

git clone https://github.com/metabrainz/docker-helpers.git
cd docker-helpers
./docker_install_xenial.sh
