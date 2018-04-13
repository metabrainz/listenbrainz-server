To start a node:

scp docker/setup-node.sh root@<node ip>:/root && ssh root@<node ip> /root/setup-node.sh <master ip> <swarm token>

To start the master:

export SPARK_LOCAL_IP=195.201.112.36

docker network create -d overlay spark-network

docker service rm spark-master
docker node update --label-add type=master master
docker service create --replicas 1 --name spark-master --network spark-network --env SPARK_LOCAL_IP=195.201.112.36 --constraint 'node.labels.type == master' metabrainz/spark-master

docker service rm spark-workers
docker service create --replicas 4 --name spark-workers --network spark-network --env MASTER_IP=195.201.112.36 metabrainz/spark-worker
