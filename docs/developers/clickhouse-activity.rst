Daily activity
==============

User daily activity answers “How many listens did this user submit on Mondays
between 09:00 and 10:00 UTC?” for each weekday and hour in a selected period.

.. image:: ../images/clickhouse-activity.svg
   :alt: Full and incremental dumps feed the ClickHouse listens table. A stats job snapshots hourly counts and sends per-user weekday and hour totals through RabbitMQ to CouchDB.

Running a refresh
~~~~~~~~~~~~~~~~~

.. code-block:: console

   $ python manage.py clickhouse daily_activity --range week --range month

The hourly materialized view sums listen changes by user, UTC date and hour in ``hourly_listen_counts``.
The job calls ``aggregate_snapshot(HOURLY_COUNTS)`` once and reads that
snapshot for every requested range.

Range boundaries
~~~~~~~~~~~~~~~~

The UTC time at the start of the job anchors every range, even when imports lag.
For example, on February 1, ``this_month`` selects February and ``month``
selects January. The worker sums the hourly counts by user, weekday and hour and emits only populated cells.
Completed periods end at the start of the next period, exclusively. A listen at
February 1 00:00:00 UTC belongs to February. All-time and ongoing ranges include
buckets through the current UTC date.

Each populated cell contains ``day``, ``hour`` and ``listen_count``.
