====================
ListenBrainz Scripts
====================

We have a bunch of python scripts to execute common tasks.

ListenBrainz
^^^^^^^^^^^^

These commands are helpful in running a ListenBrainz development
instance and some other miscellaneous tasks.

.. click:: listenbrainz.manage:cli
   :prog: python manage.py
   :nested: full

.. _Dump Manager:

Dump Manager
^^^^^^^^^^^^

These commands are used to export and import dumps.

.. click:: listenbrainz.db.dump_manager:cli
   :prog: python manage.py dump
   :nested: full

ListenBrainz Spark
^^^^^^^^^^^^^^^^^^

These commands are used to interact with the Spark Cluster.

.. click:: spark_manage:cli
   :prog: python spark_manage.py
   :nested: full

.. click:: listenbrainz.spark.request_manage:cli
   :prog: python manage.py spark
   :nested: full
