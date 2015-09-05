#!/bin/sh
# Application setup script for Vagrant

# If an argument is given, it's an apt archive
if [ $# -eq 1 ]; then
  echo "Setting apt mirror to $1"
  sed -i "s/archive.ubuntu.com/$1/" /etc/apt/sources.list
fi

apt-get update
#apt-get -y upgrade

cd messybrainz-server
bash ./admin/install_database.sh
bash ./admin/install_web_server.sh
