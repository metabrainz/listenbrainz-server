ClickHouse stats
================

Each stat below describes the aggregate it reads, how to request a refresh
and what the result contains. Wait for the listen import to finish before
requesting fresh stats. Each job reads the counts available when it starts.

Set the Consul key ``prefer_clickhouse_stats`` to the JSON boolean ``true`` to
serve user daily and listening activity from ClickHouse-generated CouchDB
documents. If the requested user's document is missing or cannot be read or
validated, the server reads the Spark stats for the same user and range.
With the key unset or set to ``false``, the server reads Spark stats directly.
Both user activity endpoints temporarily include ``payload.source`` in
successful responses. Its value is ``clickhouse`` or ``spark``, depending
on which system generated the returned stats.

.. toctree::
   :maxdepth: 1

   clickhouse-activity
