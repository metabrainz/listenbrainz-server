from datetime import datetime

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_latest_listen_ts, get_listens_from_new_dump


def get_recording_discovery():
    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    listens_df = get_listens_from_new_dump(from_date, to_date)
    listens_df.createOrReplaceTempView("recording_discovery")

    iterator = run_query("""
        WITH discoveries AS (
            SELECT int(monotonically_increasing_id() / 25000) AS chunk_id
                   -- so that we can group rows into chunks later
                 , user_id
                 , recording_mbid
                 , first(listened_at) AS first_listened_at
                 , last(listened_at) AS latest_listened_at
              FROM recording_discovery
             WHERE recording_mbid IS NOT NULL
          GROUP BY user_id, recording_mbid
        )
        SELECT to_json(
                    named_struct(
                        'type'
                      , 'recording_discovery'
                      , 'data'
                      , collect_list(
                            struct(
                                user_id
                              , recording_mbid
                              , first_listened_at
                              , latest_listened_at
                            )
                        )
                    )
               ) AS data
          FROM discoveries
      GROUP BY chunk_id -- chunk multiple rows in 1 message to improve insertion efficiency in postgres
    """).toLocalIterator()

    for message in iterator:
        yield message.data
