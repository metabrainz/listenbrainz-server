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

## Generating Stats

To generate the stats on your local machine you will need to import the listens into HDFS. 
You should use the ``listenbrainz-incremental-dumps`` for your local environment as the size of 
``listenbrainz-full-export-dumps`` is large for a local machine (The latest 
``listenbrainz-full-export-dump`` size is around 9.3 GB). Follow the given steps to import the 
listens.

### Update config.py

Open the ``config.py`` file present in the ``listenbrainz_spark`` directory and update the FTP 
listens directory to import the incremental dumps as given.

    FTP_LISTENS_DIR = '/pub/musicbrainz/listenbrainz/incremental/'

Now update the temporary listens directory and dump with the directory name and the .tar.xz file 
you would like to import as temporary listens. e.g. To import the 
``listenbrainz-listens-dump-127-20200210-000002-incremental`` refer the below-given code.

    TEMP_LISTENS_DIR = 'listenbrainz-dump-127-20200210-000002-incremental/'
    TEMP_LISTENS_DUMP = 'listenbrainz-listens-dump-127-20200210-000002-incremental.tar.xz'

### Upload listens to HDFS

Next open the ``bash`` terminal for  ``listenbrainz_playground_1`` container by executing the 
following command

    ./develop.sh spark exec playground bash

Make sure you have the Listenbrainz Spark server running before opening the ``bash`` terminal for  
``listenbrainz_playground_1`` container. For details on running the Listenbrainz Spark server refer 
[here](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/dev/devel-env.rst).

Next upload the listens to HDFS by running the following command.
    
    /usr/local/spark/bin/spark-submit spark_manage.py upload_listens

Now you may proceed with generating stats on your system.