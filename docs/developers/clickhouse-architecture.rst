ClickHouse architecture
=======================

ListenBrainz imports listen dumps into ClickHouse and uses materialized
aggregates to compute stats. The management commands queue jobs in PostgreSQL.
The ClickHouse query worker claims import and stats jobs. Stats results travel
through RabbitMQ to a separate consumer that writes them to CouchDB.

.. toctree::
   :maxdepth: 2

   clickhouse-imports
   clickhouse-stats

Metadata caches
---------------

Run ``python manage.py clickhouse update_metadata_cache`` to queue the
ClickHouse equivalent of Spark's ``import.pg_metadata_tables`` job.
The worker reads MusicBrainz PostgreSQL through ``MB_DATABASE_URI`` and
refreshes these ClickHouse tables using the same source queries as Spark.

* ``artist_country_cache`` contains three-letter ISO country codes.
  ``artist_credit_cache`` preserves credit positions and join phrases.
* ``recording_length_cache`` includes recording redirects.
  ``recording_artist_cache``, ``release_metadata_cache``, and
  ``release_group_metadata_cache`` preserve the order of artist credits.
* The recording, artist, and release-group tag and genre caches are all keyed
  by recording MBID. For example, ``artist_genre_cache`` contains genre counts
  contributed by the recording's credited artists.

The job also builds ``artist_metadata_cache`` with the MusicBrainz integer
artist ID, MBID, and canonical name for every artist, including those without
a country match. It refreshes ``recording_feedback_cache`` from ListenBrainz
PostgreSQL. With MusicBrainz unconfigured, only the feedback cache refreshes.

For each cache, the worker streams rows into a session-local ClickHouse
table, then replaces the live table's single partition atomically. Readers
keep the previous contents if loading fails. ClickHouse discards temporary
tables when the session expires. Retrying the job refreshes all caches.
If jobs overlap, the last successful publication wins for each table.

Listen changes and aggregates
-----------------------------

The importer sends accepted listens to ``listen_changes``, a ClickHouse Null
table. It forwards each block to the registered materialized views and stores
no rows itself. Inserts carry ``delta = 1``. Before deleting a listen the
importer sends its existing values with ``delta = -1``. A correction sends the
old row and its replacement, so a count can move between groups. Replaying an
already imported dump contributes zero new rows.

Each registered materialized view reads the listen columns it needs from the
change stream and updates its target table. Stats that group listens by the
same keys can share a target. A worker can use ``aggregate_snapshot`` to clone
a target once and read consistent counts across several queries. The clone
shares immutable data parts with the live table. The worker drops the clone
on exit, and ClickHouse removes it if an abandoned session expires.

Adding a materialized aggregate
-------------------------------

Declare a ``ListenAggregate`` in
``listenbrainz/clickhouse/query_worker/listens/aggregate_tables.py`` and add it
to ``LISTEN_AGGREGATES``. Each declaration supplies the target table name,
required listen columns, target column types, table engine and a SELECT over
``{source}``. The SELECT receives the declared columns and the signed
``delta``. For an additive count use ``sum(delta)`` and a signed target column.
For a conditional count use ``sumIf(delta, condition)``. On read, sum the
stored counts per key because SummingMergeTree can still be merging parts.

Run ``python manage.py clickhouse init_schema`` with the importer idle.
Initialization reads the existing listens once to populate all newly registered
tables and preserves existing aggregates. Incremental imports also run
initialization. Full imports build their replacements from the dump in staging.
Each subsequent insert or deletion feeds the registered views through the
same stream. Adding another range or stat that can already use an existing
table only needs a reader.
