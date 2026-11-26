Listening activity
==================

Run ``python manage.py clickhouse listening_activity --range month`` to refresh
the per-user listening histogram from ``hourly_listen_counts``.

Completed ranges cover the last two calendar periods. Ongoing ranges compare
the period containing yesterday with its predecessor, through yesterday UTC.
Week, month and quarter reports have daily buckets. Half-year and year reports
have monthly buckets. All-time reports have yearly buckets from 2002 and count
listens through the current UTC date.

Each active user gets a chronological list of buckets with a ``time_range``
label, inclusive ``from_ts`` and ``to_ts`` in Unix seconds, and a
``listen_count`` of zero for buckets without listens.
