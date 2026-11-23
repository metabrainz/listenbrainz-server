ClickHouse listen imports and deletions
=======================================

Start with a full dump to populate ClickHouse. Once it succeeds, use the
incremental import to catch up with subsequent dumps.

.. code-block:: console

   $ python manage.py clickhouse import_full_dump
   $ python manage.py clickhouse import_incremental_dump

Run one import or schema initialization at a time. Import preparation removes
leftover staging tables. See :doc:`../maintainers/dumps` for operational details.

Staging and publication
-----------------------

During import, the worker loads the dump's Parquet rows into a private staging
table. This lets an incomplete file load be discarded. The importer applies
deletion records to stored and staged listens. For a full dump it swaps the
completed staging table into ``listens``. For an incremental dump it merges
new listen keys and keeps the newest submission for each key. When replacing
existing submissions, it applies the changes to a clone before swapping it in.

A full import builds a private change stream, views and targets while loading
the Parquet files, then replaces the live data. Incremental imports feed the
live stream described in :doc:`clickhouse-architecture`.

Applying deletions
------------------

Each import copies completed listen deletions and per-user history cutoffs
from PostgreSQL into ClickHouse. An individual deletion matches a specific
listen version. A history deletion removes a user's listens created before
the cutoff. ClickHouse retains these records so replaying an older dump
cannot restore deleted listens. An incremental import applies pending
deletions even when there are no new dump files.

Interrupted imports
-------------------

If an import stops partway through a live write, aggregate counts can diverge
from the stored listens. Retrying the incremental import can apply a change
twice. To restore consistent counts, run a full dump import and catch up with
incremental dumps before refreshing stats.
