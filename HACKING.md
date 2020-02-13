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

To generate the stats on your local machine you will need to upload the listens to HDFS. 
On a local machine, ``listenbrainz-incremental-dumps`` should be used since the size of ``listenbrainz-full-export-dumps`` is large for a local machine (The latest ``listenbrainz-full-export-dump`` size is around 9.3 GB). Follow the given steps to import the 
listens.

### Update config.py

Open the ``config.py`` file present in the ``listenbrainz_spark`` directory and update the FTP_LISTENS_DIR with the directory name from where the dumps will be fetched from the FTP server.

    FTP_LISTENS_DIR = '/pub/musicbrainz/listenbrainz/incremental/'

Update TEMP_LISTENS_DIR with the directory name and TEMP_LISTENS_DUMP with the .tar.xz file. 
Refer the [FTP server](http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/) website for the
name of directory and tar.xz file.

e.g. To import the ``listenbrainz-listens-dump-127-20200210-000002-incremental`` refer the example given below.

    TEMP_LISTENS_DIR = 'listenbrainz-dump-127-20200210-000002-incremental/'
    TEMP_LISTENS_DUMP = 'listenbrainz-listens-dump-127-20200210-000002-incremental.tar.xz'

### Upload listens to HDFS

Open the ``bash`` terminal for  ``listenbrainz_playground_1`` container by executing the following command

    ./develop.sh spark exec playground bash

Make sure to have ListenBrainz Spark running before opening the ``bash`` terminal for  
``listenbrainz_playground_1`` container. For details on running ``ListenBrainz Spark`` refer 
[here](https://github.com/metabrainz/listenbrainz-server/blob/master/docs/dev/devel-env.rst).

Upload the listens to HDFS by running the following command.
    
    /usr/local/spark/bin/spark-submit spark_manage.py upload_listens

This command first downloads the listens dump from the FTP server and then uploads the listens to HDFS.

Now you may proceed with generating stats on your system.