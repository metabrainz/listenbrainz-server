User top release groups
=======================

Run ``python manage.py clickhouse release_groups --range month`` to refresh
per-user top release groups. Omit ``--range`` to refresh all nine ranges.
The worker uses the same UTC calendar boundaries as :doc:`clickhouse-artists`.
The latest day with listens anchors the ranges, even if those listens have
no release title.

Editions of the same MusicBrainz release group count together. The group's
title, ordered artist credits and cover art come from MusicBrainz. If either
the release or its group is missing from the caches, the worker groups listens
by the case-insensitive submitted release title and artist name, along with
the ordered artist MBIDs. These entries have a null release group MBID.
Listens with a missing or empty resolved title are excluded.

Each document contains the total number of distinct groups in the range
and up to 1,000 groups ordered by listen count. Ties use descending title,
group MBID, artist name and artist MBIDs.

Building the daily counts
-------------------------

On an existing installation, queue ``python manage.py clickhouse update_metadata_cache``
before ``python manage.py clickhouse init_schema`` to backfill mapped groups.
The build takes a snapshot of the release-to-group mapping and group metadata.
With empty caches, listens use their submitted metadata. A full listen import
rebuilds the daily counts with the latest caches.

``user_release_group_stats_daily`` stores signed counts by user, UTC day and
group key. ``release_group_metadata`` stores the display fields for each key.
Incremental imports, corrections and deletions use the mapping from the same
build, so a later cache refresh cannot move a deletion to a different group.
