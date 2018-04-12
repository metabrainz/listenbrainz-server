#!/bin/sh

echo "wait for $MASTER_IP to start."

export SPARK_NO_DAEMONIZE=1

dockerize -wait tcp://${MASTER_IP}:7077 /usr/local/spark/sbin/start-slave.sh spark://${MASTER_IP}:7077
