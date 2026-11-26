User top recordings
===================

Run ``python manage.py clickhouse init_schema`` to backfill daily recording
counts and metadata from existing listens. To refresh the previous month's
rankings, run ``python manage.py clickhouse recordings --range month``.
Omit ``--range`` to refresh all nine ranges. The UTC boundaries follow
:doc:`clickhouse-artists`.

Recordings are grouped by the submitted track, artist and release names,
recording and release MBIDs, and ordered artist MBIDs. Names are compared
case-insensitively. The same recording on two different releases has a
separate count for each release. Listens without a release still count.

Daily recording counts
----------------------

``user_recording_stats_daily`` has five columns.

.. code-block:: sql

   user_id          UInt32,
   day              Date,
   recording_id     UInt128,
   release_group_id Tuple(Bool, UUID),
   listen_count     Int64

``recording_id`` hashes the exact submitted track, artist and release names,
recording and release MBIDs, and ordered artist MBIDs. ``recording_metadata``
stores those fields by ID. This preserves each edition and spelling when
the worker sums signed counts over a range.

``release_group_id`` uses the same pinned mapping and fallback hash as
:doc:`clickhouse-release-groups`. An untitled, unmapped release uses an empty
title in the hash so the recording still counts. A full import rebuilds the
keys from the current mapping. Incremental corrections and deletions use the
same mapping as the original counts.

For each range the worker displays the lexicographically smallest remaining
combination of track, artist and release names.
It ranks recordings by listen count, breaking ties by track title, recording
MBID, artist name, artist MBIDs, release title and release MBID in descending
order. Each document contains the total and up to 1,000 recordings. As in
Spark, ranked entries with an empty artist name are dropped from both.

The worker reads ordered artist credits from ``recording_artist_cache`` and
cover art from ``release_metadata_cache``. Run ``python manage.py clickhouse
update_metadata_cache`` to update those fields for the next stats refresh.
If either cache is missing, its fields are null. Updating metadata does
not require rebuilding the daily counts.
