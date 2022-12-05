import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_most_prominent_color(year):
    setup_listens_for_year(year)
    _get_release_colors().createOrReplaceTempView("release_color")
    all_user_colors = run_query(_get_most_prominent_color()).collect()
    yield {
        "type": "most_prominent_color",
        "year": year,
        "data": all_user_colors[0]["all_users_colors"]
    }


def _get_release_colors():
    return listenbrainz_spark.sql_context.read.json(path.RELEASE_COLOR_DUMP)


def _get_most_prominent_color():
    return """
        WITH user_colors AS (
            SELECT user_id
                 , color
                 , count(*) as listen_count
              FROM listens_of_year l
              JOIN release_color
                ON release_color.release_mbid = l.release_mbid
             WHERE l.release_mbid IS NOT NULL
          GROUP BY user_id
                 , color
        ), ranked_user_colors AS (
            SELECT user_id
                 , color
                 , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
              FROM user_colors
        )
        SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_id, color)
                        )
                    )
                ) AS all_users_colors
          FROM ranked_user_colors
         WHERE row_number = 1
    """
