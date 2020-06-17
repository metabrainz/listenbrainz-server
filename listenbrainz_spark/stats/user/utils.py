import time
from collections import defaultdict
from datetime import datetime

from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import adjust_days, adjust_months, run_query
from listenbrainz_spark.utils import get_listens


def get_latest_listen_ts():
    """ Get the timestamp of the latest timestamp present in spark cluster """
    now = datetime.now()
    while True:
        try:
            df = get_listens(now, now, LISTENBRAINZ_DATA_DIRECTORY)
            break
        except HDFSException:
            now = adjust_months(now, 1)

    df.createOrReplaceTempView('latest_listen_ts')
    result = run_query("SELECT MAX(listened_at) as max_timestamp FROM latest_listen_ts")
    rows = result.collect()
    return rows[0]['max_timestamp']


def filter_listens(df, from_date, to_date):
    """
    Filter the given dataframe to return listens which lie between from_date and to_date

    Args:
        df: Dataframe which has to filtered
        from_time(datetime): Start date
        to_time(datetime): End date

    Returns:
        result: Dateframe with listens which lie beween from_date and to_date
    """
    result = df.filter(df.listened_at.between(from_date, to_date))
    return result


def get_last_monday(date):
    """ Get date for Monday before 'date' """
    return adjust_days(date, date.weekday())


def create_messages(data, entity, stats_type, stats_range, from_ts, to_ts):
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data (iterator): Data to sent to the webserver
        entity (str): The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_type (str): The type of statistics calculated
        stats_range (str): The range for which the statistics have been calculated
        from_ts (int): The UNIX timestamp of start time of the stats
        to_ts (int): The UNIX timestamp of end time of the stats

    Returns:
        messages (generator): A list of messages to be sent via RabbitMQ
    """
    for entry in data:
        _dict = entry.asDict(recursive=True)
        yield {
            'musicbrainz_id': _dict['user_name'],
            'type': stats_type,
            'range': stats_range,
            'from_ts': from_ts,
            'to_ts': to_ts,
            'data': _dict[entity],
            'entity': entity,
            'count': len(_dict[entity])
        }
