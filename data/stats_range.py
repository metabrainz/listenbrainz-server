"""Calendar periods used by the user statistics jobs."""
from datetime import date, datetime, time

from dateutil.relativedelta import MO, relativedelta

LAST_FM_FOUNDING_YEAR = 2002


def get_last_half_year_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous half year."""
    month = _date.month
    if month <= 6:
        # currently, in Jan-Jun previous half year is last year's Jul-Dec
        return relativedelta(years=-1, month=7, day=1)
    else:
        # currently, in Jul-Dec previous half year is Jan-Jun
        return relativedelta(month=1, day=1)


def get_last_quarter_offset(_date: date) -> relativedelta:
    """ Given a month, returns the relativedelta offset to get
    the beginning date of the previous quarter."""
    month = _date.month
    if month <= 3:
        # currently, in Jan-Mar, so previous quarter is last year's Oct-Dec
        return relativedelta(years=-1, month=10, day=1)
    elif month <= 6:
        # currently, in Apr-Jun previous is Jan-Mar
        return relativedelta(month=1, day=1)
    elif month <= 9:
        # currently, in Jul-Sep, previous is Apr-Jun
        return relativedelta(month=4, day=1)
    else:
        # currently, in Oct-Dec previous is Jul-Sep
        return relativedelta(month=7, day=1)


# listening activity stats uses a different function to calculate time ranges
# if making modifications here, remember to check and update that as well
def dates_for_stats_range(stats_range: str, as_of: datetime) -> tuple[datetime, datetime]:
    """Return the calendar range containing or preceding the supplied reference date."""
    if stats_range == "all_time":
        return datetime(LAST_FM_FOUNDING_YEAR, 1, 1, tzinfo=as_of.tzinfo), as_of

    anchor_date = as_of.date()

    # from_offset: this is applied to the anchor_date to get from_date
    # to_offset: this is applied to from_date to get to_date

    # "this" time ranges, these count stats for the ongoing time period till date
    if stats_range == "this_week":
        from_offset = relativedelta(weekday=MO(-1))
        to_offset = relativedelta(weeks=+1)
    elif stats_range == "this_month":
        from_offset = relativedelta(day=1)
        to_offset = relativedelta(months=+1)
    elif stats_range == "this_year":
        from_offset = relativedelta(month=1, day=1)
        to_offset = relativedelta(years=+1)

    # following are "last" week/month/year stats, here we want the stats of the
    # previous week/month/year and *not* from 7 days ago to today so on.

    elif stats_range == "week":
        from_offset = relativedelta(weeks=-1, weekday=MO(-1))  # monday of previous week
        to_offset = relativedelta(weeks=+1)
    elif stats_range == "month":
        from_offset = relativedelta(months=-1, day=1)  # first day of previous month
        to_offset = relativedelta(months=+1)
    elif stats_range == "quarter":
        from_offset = get_last_quarter_offset(anchor_date)
        to_offset = relativedelta(months=+3)
    elif stats_range == "half_yearly":
        from_offset = get_last_half_year_offset(anchor_date)
        to_offset = relativedelta(months=+6)
    else:  # year
        from_offset = relativedelta(years=-1, month=1, day=1)  # first day of previous year
        to_offset = relativedelta(years=+1)

    from_date = anchor_date + from_offset
    to_date = from_date + to_offset

    # set time to 00:00
    from_date = datetime.combine(from_date, time.min, tzinfo=as_of.tzinfo)
    to_date = datetime.combine(to_date, time.min, tzinfo=as_of.tzinfo)

    return from_date, to_date
