import logging

from listenbrainz_spark.recommendations.dataframe_utils import get_dates_to_train_data
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump

logger = logging.getLogger(__name__)

TOP_LISTENS_LIMIT = 1000


def get_missing_mb_data():
    return run_query(f"""
        WITH grouped_listens AS (
            SELECT user_id
                 , max(listened_at) AS max_listened_at
                 , recording_msid
                 , recording_name
                 , artist_name
                 , release_name
                 , count(*) AS listen_count
              FROM missing_mb_listens
             WHERE recording_mbid IS NULL
               AND recording_name != ''
               AND artist_name != ''
          GROUP BY user_id
                 , recording_msid
                 , recording_name
                 , artist_name
                 , release_name
        ), filtered_listens AS (
            SELECT user_id
                 , max_listened_at
                 , recording_msid
                 , recording_name
                 , artist_name
                 , release_name
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM grouped_listens
        )   SELECT user_id
                 , sort_array(
                    collect_list(
                        struct(
                            date_format(max_listened_at, "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'") AS listened_at
                          , recording_msid  
                          , recording_name
                          , artist_name
                          , release_name
                        )
                    )
                    , false
                   ) as data
              FROM filtered_listens
             WHERE rank <= {TOP_LISTENS_LIMIT}
          GROUP BY user_id
    """).toLocalIterator()


def main(days: int):
    """
    Send messages for data that has been submitted to ListenBrainz but is missing from MusicBrainz.
    To avoid overwhelming amount of data, only top `TOP_LISTENS_LIMIT` number of listens for each user
    are sent.

    Args:
        days: Number of days to calculate missing MB data from.
    """
    logger.info('Fetching listens to find missing MB data...')
    to_date, from_date = get_dates_to_train_data(days)
    listens_df = get_listens_from_dump(from_date, to_date)
    listens_df.createOrReplaceTempView("missing_mb_listens")

    missing_musicbrainz_data_itr = get_missing_mb_data()

    for row in missing_musicbrainz_data_itr:
        missing_data = row.asDict(recursive=True)
        yield {
            "type": "missing_musicbrainz_data",
            "user_id": missing_data["user_id"],
            "missing_musicbrainz_data": missing_data["data"],
            "source": "cf"
        }
