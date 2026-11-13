==========
Data Dumps
==========


ListenBrainz provides data dumps that you can import into your own server or
use for other purposes. The full data dumps are created twice a month
and the incremental data dumps twice a week.
Each dump contains a number of different files. Depending on your use cases,
you may or may not require all of them.

We have a bunch of :ref:`commands <Dump Manager>` which may be useful in interacting with dumps
during local development as well.


Dump mirrors
============
See the `ListenBrainz data page <https://listenbrainz.org/data>`_ for information about where to download the data dumps from.

File Descriptions
=================

A ListenBrainz data dump consists of three archives:

#. ``listenbrainz-public-dump.tar.zst``

#. ``listenbrainz-listens-dump.tar.zst``

#. ``listenbrainz-listens-dump-spark.tar.zst``

The database dumps and the listens dumps are created by separate jobs, so they are published in two directories per
dump cycle. The ``listenbrainz-public-dump.tar.zst`` archive is in the directory whose name ends in ``-db`` and the
listens archives are in the directory whose name ends in ``-full``. Their ids and timestamps do not match each other,
so always pick the newest directory of each kind.


listenbrainz-public-dump.tar.zst
-------------------------------

This file contains information about ListenBrainz users and statistics derived
from listens submitted to ListenBrainz calculated from users, artists, recordings etc.


listenbrainz-listens-dump.tar.zst
--------------------------------

This is the core ListenBrainz data dump. This file contains all the listens
submitted to ListenBrainz by its users.


listenbrainz-listens-dump-spark.tar.zst
--------------------------------------

This is also a dump of the core ListenBrainz listen data. These dumps are
made for consumption by the ListenBrainz Apache Spark cluster, formatting
all listens into parquet files that can easily be loaded into dataframes.
Full dumps contain one numbered parquet file per nonempty database partition,
keeping each user's listens together. Incremental dumps contain a single parquet
file in submission order. Files are written in bounded row groups and may be large.


Structure of the listens dump
=============================

The ListenBrainz listen dump consists of numbered listens files in the ``listens``
directory:

#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/0.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/1.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2.listens``

In a full dump, each file holds all the listens of a group of users, sorted by user id
and then by listened_at, newest first. The listens of a user are never split across
files. An incremental dump has a single file, ``0.listens``, with the listens submitted
since the previous dump, sorted by the time they were submitted.

Each of the .listens files contains one JSON document per line -- each
of the JSON documents is one listen, formatted in the standard listens format.

Incremental dumps
=================

ListenBrainz provides incremental data dumps that you can use to keep up to date with
the ListenBrainz dataset without needing to download the full dumps everytime. These
dumps have the same structure as the corresponding full dumps, but only contain
data that has been submitted since the creation of the previous dump. We create
incremental data dumps daily.

The basic idea here is that dumps create a linear timeline of the dataset
based on the time of submission of data. In order to use the incremental dumps,
you must start with the latest full dump and then, applying all incremental dumps
since will give you the latest data. The series is consistent, if you
take a full dump and apply all incremental dumps since that full dump until the
next full dump, you will have all data as the next full dump.

.. warning::

  Deleted listens present a tricky problem in this setup, since they are not included
  in the incremental dumps. To get a fully accurate list of listens, with deleted
  listens removed, you'll need to re-import a full dump.
