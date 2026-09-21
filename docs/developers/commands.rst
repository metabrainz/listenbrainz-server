=======
Scripts
=======

We have a bunch of python scripts to execute common tasks.

.. note::

    During development, you can use :code:`./develop.sh manage ...` to execute
    the commands. In production, the command should be run inside the appropriate
    container using :code:`python manage.py ...`.

ListenBrainz
^^^^^^^^^^^^

These commands are helpful in running a ListenBrainz development
instance and some other miscellaneous tasks.

The site-status listen graph is populated by
:code:`./develop.sh manage refresh_listen_count_evolution`. Run it once to populate
an empty cache; production cron refreshes it daily. The cache has no expiry.
Daily refreshes recount only the current submission month. The first refresh after
rollover also finalizes the previous month once. If refreshes have been missed,
recounting starts at the last cached month to catch up. Finalized months are reused.
Page requests only read the cached result, and failed refreshes leave it intact.

The initial build (or rebuilding after cache eviction) scans the full Timescale
listen table. To reconcile older deletions, explicitly run
:code:`./develop.sh manage refresh_listen_count_evolution --full`, which also scans
all listens. Both operations run offline.

.. click:: listenbrainz.manage:cli
   :prog: ./develop.sh manage
   :nested: full

.. _Dump Manager:

Dump Manager
^^^^^^^^^^^^

These commands are used to export and import dumps.

.. click:: listenbrainz.dumps.manager:cli
   :prog: ./develop.sh manage dump
   :nested: full

ListenBrainz Spark
^^^^^^^^^^^^^^^^^^

These commands are used to interact with the Spark Cluster.

.. click:: spark_manage:cli
   :prog: python spark_manage.py
   :nested: full

.. click:: listenbrainz.spark.request_manage:cli
   :prog: ./develop.sh manage spark
   :nested: full
