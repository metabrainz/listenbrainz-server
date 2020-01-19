#!/bin/sh

if [ "$#" -ne 2 ]; then
    echo "Usage: setup-node.sh <master ip> <swarm token>"
    exit
fi

MASTER_IP=$1
SWARM_TOKEN=$2

ufw --force enable
ufw allow 22/tcp
ufw allow 2377/tcp
ufw allow 4789/udp
ufw allow 7946

apt-get update
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

apt-get update
apt-get install -y docker-ce

docker swarm join --token $SWARM_TOKEN $MASTER_IP:2377

docker node update --label-add type=worker `hostname`

docker volume create --driver local hdfs-volume
docker volume create --driver local spark-volume

docker run \
    --mount type=volume,source=hdfs-volume,destination=/home/hadoop/hdfs \
    metabrainz/hadoop-yarn:beta /usr/local/hadoop/bin/hdfs namenode -format

reboot
