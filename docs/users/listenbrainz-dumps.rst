=======================
ListenBrainz Data Dumps
=======================


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

#. ``listenbrainz-public-dump.tar.xz``

#. ``listenbrainz-listens-dump.tar.xz``

#. ``listenbrainz-listens-dump-spark.tar.xz``


listenbrainz-public-dump.tar.xz
-------------------------------

This file contains information about ListenBrainz users and statistics derived
from listens submitted to ListenBrainz calculated from users, artists, recordings etc.


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

The ListenBrainz listen dump consists of listens broken down by year and month.
At the top level there are directories for each of the year for which we have
data. Inside each year there are listens files with month number as its name:

#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2005/1.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2005/2.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2005/3.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2005/4.listens``
#. ``listenbrainz-listens-dump-183-20200727-001004-full/listens/2005/5.listens``

Each of the .listens files contains one JSON document per line -- each
of the JSON documents is one listen, formatted in the standard listens format.

Incremental dumps (BETA)
========================

.. warning::

    The incremental dumps are in beta. We know of some data consistency issues where
    incremental dumps have fewer listens than they should. Make
    sure you use the full dumps if data accuracy is important.

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
