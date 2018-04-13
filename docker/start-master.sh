#!/bin/sh

# must set export SPARK_LOCAL_IP=195.201.112.36

export SPARK_NO_DAEMONIZE=1
/usr/local/spark/sbin/start-master.sh
