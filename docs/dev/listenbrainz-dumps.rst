=======================
ListenBrainz Data Dumps
=======================


ListenBrainz provides data dumps that you can import into your own server or
use for other purposes. The full data dumps are created twice a month
and the incremental data dumps twice a week.
Each dump contains a number of different files. Depending on your use cases,
you may or may not require all of them.


File Descriptions
=================

A ListenBrainz data dump consists of three archives:

#. ``listenbrainz-public-dump.tar.xz``

#. ``listenbrainz-listens-dump.tar.xz``

#. ``listenbrainz-listens-dump-spark.tar.xz``


listenbrainz-public-dump.tar.xz
-------------------------------

This file contains information about ListenBrainz users and statistics derived
from listens submitted to ListenBrainz calculated using Google BigQuery about
users, artists, recordings etc.


listenbrainz-listens-dump.tar.xz
--------------------------------

This is the core ListenBrainz data dump. This file contains all the listens
submitted to ListenBrainz by its users.


listenbrainz-listens-dump-spark.tar.xz
--------------------------------------

This is also a dump of the core ListenBrainz listen data. These dumps are
made for consumption by the ListenBrainz Apache Spark cluster, formatting
all listens into monthly JSON files that can easily be loaded into dataframes.


Structure of the listens dump
=============================

The ListenBrainz listens dump consists of a number of files containing listens
in JSON format, one document per line. Each user's listens are listed in one file in chronological
order, with the latest listen first. The exact location of each user's listens is
listed in the ``index.json`` file which is a JSON document containing a file name,
an offset and size (in bytes) to uniquely identify the location and size of each user's
listens.


The format of the ``index.json`` file is as follows::

    {
        'user1': {
            'file_name': "file which contains user1's listens",
            'offset': "the byte at which user1's listens begin in the file",
            'size': "the size (in bytes) of the user's listens"
        }
    }


Hence, if you wanted to extract a particular user's listens, you would look up that
user in the ``index.json`` file, find the filename and offset from there, open the
file and seek to that byte and read the bytes specified by the ``index.json`` files.
Each line in the part of the file we read is a listen submitted for that particular
user.


`Here <https://github.com/metabrainz/listenbrainz-server/blob/master/docs/dev/dump_examples/read_listens_dump.py>`_ is some example code to explain the mentioned way of parsing the listens dump.


Incremental dumps
=================

ListenBrainz provides incremental data dumps that you can use to keep up to date with
the ListenBrainz dataset without needing to download the full dumps everytime. These
dumps have the same structure as the corresponding full dumps, but only contain
data that has been submitted since the creation of the previous dump. We create
incremental data dumps twice a week.

The basic idea here is that dumps create a linear timeline of the dataset
based on the time of submission of data. In order to use the incremental dumps,
you must start with the latest full dump and then, applying all incremental dumps
since will give you the latest data. The series is consistent, if you
take a full dump and apply all incremental dumps since that full dump until the
next full dump, you will have the same data as the next full dump.