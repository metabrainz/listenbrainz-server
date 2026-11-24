ClickHouse stats
================

.. toctree::
   :maxdepth: 1

   clickhouse-activity
   clickhouse-listening-activity
   clickhouse-artists

Refreshing stats
----------------

Wait for the listen import to finish before requesting fresh stats. Each
command accepts repeated ``--range`` options. Omitting ``--range`` refreshes
all nine ranges. A job reads one snapshot for every range it refreshes.

CouchDB delivery
----------------

For each range the worker publishes a start message, batches of up to 25
users, and an end message containing the expected user count. The consumer
writes one document per user ID to ``clickhouse_<stat>_<range>_<generation>``.
Each document includes the range timestamps.

On a transient CouchDB request failure the consumer requeues the message.
Other prefetched results may be processed before redelivery. The consumer
checks the stored document count before removing older unlocked generations
for that range. A count mismatch preserves the previous generation. A
successful empty range retires old results in the same way.

Serving stats
-------------

Set the Consul key ``prefer_clickhouse_stats`` to ``yes`` to serve these stats
from ClickHouse-generated CouchDB documents. If the requested user's
document is missing or fails to load or validate, the server reads the
Spark stats for the same user and range. With the key unset or set to
``no``, the server reads Spark stats directly.

The daily and listening activity endpoints include ``payload.source`` in
successful responses. Its value is ``clickhouse`` or ``spark``, depending on
which system generated the returned stats.
