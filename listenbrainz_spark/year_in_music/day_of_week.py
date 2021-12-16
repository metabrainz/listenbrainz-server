from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_day_of_week(year):
    setup_listens_for_year(year)
    query = """
        WITH listen_weekday AS (
              SELECT user_name
                   , date_format(listened_at, 'EEEE') AS weekday
                   , count(*) AS listen_count
                FROM listens_of_year
            GROUP BY user_name
                   , weekday
        ), top_listen_weekday AS (
              SELECT user_name
                   , weekday
                   , listen_count
                   , row_number() OVER(PARTITION BY user_name ORDER BY listen_count DESC) AS row_number
                FROM listen_weekday
        )
        SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_name, weekday)
                        )
                    )
                ) AS all_users_weekday
          FROM top_listen_weekday
         WHERE row_number = 1
    """
    data = run_query(query).collect()
    yield {
        "type": "day_of_week",
        "data": data[0]["all_users_weekday"]
    }
