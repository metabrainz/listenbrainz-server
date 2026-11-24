User top artists
================

Run ``python manage.py clickhouse artists --range month`` to refresh per-user
top artists. The worker pins the materialized ``user_artist_stats_daily``
table once per refresh. The latest UTC day with listens anchors the ranges.
Ongoing ranges use the period containing the previous day. Each range includes
its start and excludes its end. A listen at February 1 00:00 UTC belongs to
February. All-time stats end at midnight UTC following the latest listen day.

Each artist in a credit receives one count per occurrence. A missing or empty
credit list contributes one listen with a null artist MBID. Groups are keyed
by MBID and case-insensitive display name, using the submitted credit when
the canonical name is null. Empty names are discarded after ranking, matching
Spark's adjustment to the total count. Each document retains up to 1,000
artists. Ties use descending display name and MBID, including at the cutoff.

The listens table stores artist credits as ``Array(UUID)``. Uppercase and
lowercase spellings of the same MBID group together and use the same
MusicBrainz lookup. Individual array elements must be valid UUIDs. A stored
all-zero UUID remains distinct from the null MBID produced by an empty list.

Daily artist counts
-------------------

Run ``python manage.py clickhouse init_schema`` to backfill daily counts from
existing listens. The materialized view groups signed listen changes by user,
UTC day and artist ID and stores their net listen count. Incremental imports,
corrections and deletions update these counts through the same stream as
hourly activity.

The separate ``artist_metadata`` table stores the MBID and display name for
each artist ID. Unmapped artists use the lexicographically smallest submitted
spelling seen across all users since the full build.
The stats worker uses these names to order artists tied at the cutoff.

For a known MBID, ``artist_id`` is the integer ``musicbrainz.artist.id``.
The lookup includes artists whose area has no country match, so their
canonical names are available even when Spark's artist country cache omits them.
For other credits, ClickHouse hashes the MBID and lowercase submitted name
into a UInt128 with its high bit set. This keeps generated IDs stable across
imports and separate from MusicBrainz IDs.

Updating MusicBrainz metadata
-----------------------------

Run ``python manage.py clickhouse update_metadata_cache`` to populate
``artist_metadata_cache`` from MusicBrainz. The first artist backfill and
each full listen import take a local snapshot of this table. If the cache
is absent or empty, artist counts use the submitted names and generated IDs.
Queue the metadata update before the first backfill or full import to use
MusicBrainz IDs immediately. Later updates take effect when the artist
aggregates are rebuilt, normally on the next full import. Incremental imports
and deletions keep using the lookup paired with the live counts.
