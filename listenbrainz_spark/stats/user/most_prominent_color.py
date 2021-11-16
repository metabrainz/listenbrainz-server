from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump


def get_most_prominent_color():
    _get_release_colors().createOrReplaceTempView("release_color")
    _get_2021_listens().createOrReplaceTempView("listens_2021")
    all_user_colors = run_query(_get_most_prominent_color()).collect()
    yield {
        "type": "most_prominent_color",
        "data": all_user_colors[0]["all_users_colors"]
    }


def _get_release_colors():
    return listenbrainz_spark.sql_context.read.json(path.RELEASE_COLOR_DUMP)


def _get_2021_listens():
    start = datetime(2021, 1, 1, 0, 0, 0)
    end = datetime.now()
    return get_listens_from_new_dump(start, end)


def _get_most_prominent_color():
    return """
        WITH user_colors AS (
            SELECT user_name
                 , color
                 , count(*) as listen_count
              FROM listens_2021 l
              JOIN release_color
                ON release_color.release_mbid = l.release_mbid
             WHERE l.release_mbid IS NOT NULL
          GROUP BY user_name
                 , color
        ), ranked_user_colors AS (
            SELECT user_name
                 , color
                 , row_number() OVER(PARTITION BY user_name ORDER BY listen_count DESC) AS row_number
              FROM user_colors
        )
        SELECT to_json(
                    collect_list(
                        struct(user_name, color)
                    )
                ) AS all_users_colors
          FROM ranked_user_colors
         WHERE row_number = 1
    """
