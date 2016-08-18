#!/bin/bash

# install docker
command -v docker >/dev/null 2>&1
rc=$?
if [[ $rc != "0" ]]; then
    curl -sSL https://get.docker.com/ | sh

    # add ubuntu user to docker group
    sudo usermod -aG docker vagrant
fi

# install docker-compose
command -v docker-compose >/dev/null 2>&1
rc=$?
if [[ $rc != "0" ]]; then
    curl -L https://github.com/docker/compose/releases/download/1.6.2/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "ListenBrainz VM created, build containers"

cd /vagrant/vagrant
./run-server.sh
