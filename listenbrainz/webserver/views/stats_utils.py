""" Helpers for deriving values from precomputed statistics.

    Kept free of Flask/DB imports so the pure logic can be unit tested in
    isolation.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta

#: Offset from the start of the previous period to the start of the current
#: period, for each listening-activity range. The listening_activity stat spans
#: two consecutive periods (previous + current) so the website can render a
#: comparison, so the current period begins one such offset after the stat's
#: first segment.
LISTENING_ACTIVITY_PERIOD_OFFSET = {
    "this_week": relativedelta(weeks=1),
    "week": relativedelta(weeks=1),
    "this_month": relativedelta(months=1),
    "month": relativedelta(months=1),
    "quarter": relativedelta(months=3),
    "half_yearly": relativedelta(months=6),
    "this_year": relativedelta(years=1),
    "year": relativedelta(years=1),
}


def current_period_listen_count(stats_range: str, records) -> Tuple[int, Optional[int]]:
    """ Sum the listens of the *current* period of a listening_activity stat.

        The listening_activity stat stores per-segment listen counts covering
        two consecutive periods (the previous and the current one) so that the
        website can draw a comparison chart. This returns the total for the
        current (most recent) period only, matching the number displayed on
        listenbrainz.org.

        Args:
            stats_range: one of the listening-activity ranges, or ``all_time``.
            records: iterable of segments, each with ``from_ts`` and
                ``listen_count`` attributes (e.g. ListeningActivityRecord).

        Returns:
            A ``(listen_count, from_ts)`` tuple where ``from_ts`` is the start of
            the current period (or ``None`` when there are no records). For
            ``all_time`` every segment is summed since there is no previous
            period to exclude.
    """
    records = list(records)
    if not records:
        return 0, None

    base_ts = min(record.from_ts for record in records)
    if stats_range == "all_time":
        total = sum(record.listen_count for record in records)
        return total, base_ts

    offset = LISTENING_ACTIVITY_PERIOD_OFFSET[stats_range]
    period_start = datetime.fromtimestamp(base_ts, tz=timezone.utc) + offset
    period_start_ts = int(period_start.timestamp())

    total = sum(record.listen_count for record in records if record.from_ts >= period_start_ts)
    return total, period_start_ts
