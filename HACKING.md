## Useful commands

Here are some notes for short-cuts to get useful things done while hacking on ListenBrainz:

### Redis

To open a Redis command prompt:

    docker exec -it listenbrainz_redis_1 redis-cli


### Influx

To open an Influxdb command prompt:

    docker exec -it listenbrainz_influx_1 influx

and to drop all the listens in influx db:

    drop database listenbrainz

After dropping the database, you'll probably need to create the database again:

    create database listenbrainz


### Postgres

To get a postgres command prompt:

    ./develop.sh psql

### Tests

To run the unit tests:

    ./test.sh

To run the integration tests:

    ./integration-test.sh

### Spark

Listen history submitted to ListenBrainz is processed to get useful information out of it. ListenBrainz uses Apache Spark to process this big data. Since ListenBrainz services and ListenBrainz Spark services run on separate clusters, the containers are separate too. To setup ListenBrainz, ListenBrainz Spark setup is not required but since ListenBrainz Spark uses ListenBrainz network to send and recieve RabbitMQ messages, the vice versa is not true i.e. to setup ListenBrainz Spark, it is necessary to setup ListenBrainz. Here is a guide for your way around a few areas of Spark.

- ##### Format namenode
    Before formatting namenode, datanode must be formatted. To format namenode and datanode:

        ./spark_develop.sh format <datanode cluster ID>

    To open datanode command prompt:

        docker exec -it listenbrainzspark_datanode_1 bash

    To get the datanode cluster id:

        cat /home/hadoop/hdfs/datanode/current/VERSION | grep "clusterID"
    
- ##### Upload listens to HDFS

    On a local machine, ``listenbrainz-incremental-dumps`` should be used since the size of ``listenbrainz-full-export-dumps`` is large for a local machine. (The average ``listenbrainz-full-export-dump`` size is around 9 GB). Follow the given steps to import the listens.

    Open the ``bash`` terminal for  ``listenbrainz_playground_1`` container by executing the following command

        ./spark_develop.sh exec playground bash

    Make sure to have ListenBrainz Spark running before opening the ``bash`` terminal for  
    ``listenbrainz_playground_1`` container. For details on running ``ListenBrainz Spark`` refer [here](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/dev/devel-env.rst#set-up-listenbrainz-spark-development-environment).

    Upload the listens to HDFS by running the following command.
        
        /usr/local/spark/bin/spark-submit spark_manage.py upload_listens -i

    This command first fetches the name of the latest incremental dump, downloads the listens dump from the FTP server and then uploads the listens to HDFS.