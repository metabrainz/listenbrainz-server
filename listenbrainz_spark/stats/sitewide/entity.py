import json
import logging
from datetime import datetime
from typing import List, Optional

import listenbrainz_spark
from data.model.sitewide_artist_stat import SitewideArtistRecord
from data.model.sitewide_entity import SitewideEntityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (offset_days, offset_months, replace_days,
                                      run_query, get_day_end, get_year_end, get_month_end)
from listenbrainz_spark.stats.sitewide.artist import get_artists
from listenbrainz_spark.stats.utils import (filter_listens, get_last_monday,
                                            get_latest_listen_ts)
from listenbrainz_spark.utils import get_listens
from pydantic import ValidationError


logger = logging.getLogger(__name__)


entity_handler_map = {
    'artists': get_artists,
}

entity_model_map = {
    'artists': SitewideArtistRecord
}

time_range_schema = ["time_range", "from_ts", "to_ts"]


def get_entity_week(entity: str, use_mapping: bool = False) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the weekly sitewide top entity """
    logger.debug("Calculating sitewide_{}_week...".format(entity))

    date = get_latest_listen_ts()

    to_date = get_last_monday(date)
    # Set time to 00:00
    to_date = datetime(to_date.year, to_date.month, to_date.day)
    from_date = offset_days(to_date, 14)
    day = from_date

    # Genarate a dataframe containing days of last and current week along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%A %d %B %Y'), int(day.timestamp()), int(get_day_end(day).timestamp())])
        day = offset_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    table_name = 'sitewide_{}_week'.format(entity)
    filtered_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name, "EEEE dd MMMM yyyy", use_mapping)
    message = create_message(data=data, entity=entity, stats_range='week',
                             from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return message


def get_entity_month(entity: str, use_mapping: bool = False) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the montly sitewide top entity """
    logger.debug("Calculating sitewide_{}_month...".format(entity))

    to_date = get_latest_listen_ts()
    # Set time to 00:00
    to_date = datetime(to_date.year, to_date.month, to_date.day)
    from_date = replace_days(offset_months(to_date, 1, shift_backwards=True), 1)
    day = from_date

    # Genarate a dataframe containing days of last and current month along with start and end time
    time_range = []
    while day < to_date:
        time_range.append([day.strftime('%d %B %Y'), int(day.timestamp()), int(get_day_end(day).timestamp())])
        day = offset_days(day, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'sitewide_{}_month'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name, "dd MMMM yyyy", use_mapping)

    message = create_message(data=data, entity=entity, stats_range='month',
                             from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return message


def get_entity_year(entity: str, use_mapping: bool = False) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the yearly sitewide top entity """
    logger.debug("Calculating sitewide_{}_year...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = datetime(to_date.year-1, 1, 1)
    month = from_date

    time_range = []
    # Genarate a dataframe containing months of last and current year along with start and end time
    while month < to_date:
        time_range.append([month.strftime('%B %Y'), int(month.timestamp()), int(get_month_end(month).timestamp())])
        month = offset_months(month, 1, shift_backwards=False)

    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'sitewide_{}_year'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name, "MMMM yyyy", use_mapping)
    message = create_message(data=data, entity=entity, stats_range='year',
                             from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return message


def get_entity_all_time(entity: str, use_mapping: bool = False) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the all_time sitewide top entity """
    logger.debug("Calculating sitewide_{}_all_time...".format(entity))

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    # Generate a dataframe containing years from "from_date" to "to_date"
    time_range = [
        [str(year), int(datetime(year, 1, 1).timestamp()), int(get_year_end(year).timestamp())]
        for year in range(from_date.year, to_date.year + 1)
    ]
    time_range_df = listenbrainz_spark.session.createDataFrame(time_range, schema=time_range_schema)
    time_range_df.createOrReplaceTempView('time_range')

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    table_name = 'sitewide_{}_all_time'.format(entity)
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name, "yyyy", use_mapping)
    message = create_message(data=data, entity=entity, stats_range='all_time',
                             from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return message


def create_message(data, entity: str, stats_range: str, from_ts: int, to_ts: int) -> Optional[List[SitewideEntityStatMessage]]:
    """
    Create message to send the data to the webserver via RabbitMQ

    Args:
        data (iterator): Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_ts: The UNIX timestamp of start time of the stats
        to_ts: The UNIX timestamp of end time of the stats

    Returns:
        message: A list of message to be sent via RabbitMQ
    """
    message = {
        'type': 'sitewide_entity',
        'stats_range': stats_range,
        'from_ts': from_ts,
        'to_ts': to_ts,
        'entity': entity,
        'data': []
    }

    for entry in data:
        _dict = entry.asDict(recursive=True)

        entity_list = []
        for item in _dict[entity][:1000]:
            try:
                model = entity_model_map[entity](**item)
                entity_list.append(model.dict())
            except ValidationError:
                logger.warning("""Invalid entry present in sitewide {stats_range} top {entity} for
                                        time_range: {time_range}, skipping""".format(stats_range=stats_range, entity=entity,
                                                                                     time_range=_dict['time_range']))

        message["data"].append({
            entity: entity_list,
            "from_ts": _dict["from_ts"],
            "to_ts": _dict["to_ts"],
            "time_range": _dict["time_range"]
        })

    try:
        model = SitewideEntityStatMessage(**message)
        result = model.dict(exclude_none=True)
        return [result]
    except ValidationError:
        logger.error("""ValidationError while calculating {stats_range} sitewide top {entity}.
                                 Data: {data}""".format(stats_range=stats_range, entity=entity,
                                                        data=json.dumps(message, indent=4)),
                                 exc_info=True)
        return None
