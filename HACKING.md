## Useful commands

Here are some notes for short-cuts to get useful things done while hacking on ListenBrainz:

### Redis

To open a Redis command prompt:

    docker exec -it listenbrainz_redis_1 redis-cli


### Postgres

To get a postgres command prompt:

    ./develop.sh psql


### Timescale

To get a timescale/postgres command prompt:

    ./develop.sh timescale


### Tests

To run the unit tests:

    ./test.sh

To run the integration tests:

    ./integration-test.sh

### Spark

Listen history submitted to ListenBrainz is processed to get useful information out of it. ListenBrainz uses Apache Spark to process this big data.
Since ListenBrainz services and ListenBrainz Spark services run on separate clusters, the containers are separate too. To setup ListenBrainz,
ListenBrainz Spark setup is not required but since ListenBrainz Spark uses ListenBrainz network to send and recieve RabbitMQ messages,
the vice versa is not true i.e. to setup ListenBrainz Spark, it is necessary to setup ListenBrainz. Here is a guide for your way around a few areas of Spark.

- ##### Format namenode
    Before formatting namenode, datanode must be formatted. To format namenode and datanode:

        ./spark_develop.sh format <datanode cluster ID>

    To open datanode command prompt:

        docker exec -it listenbrainzspark_datanode_1 bash

    To get the datanode cluster id:

        cat /home/hadoop/hdfs/datanode/current/VERSION | grep "clusterID"
