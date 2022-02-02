from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_listen_count(year):
    setup_listens_for_year(year)
    data = run_query(_get_yearly_listen_counts()).collect()
    yield {
        "type": "year_in_music_listen_count",
        "data": data[0]["yearly_listen_counts"]
    }


def _get_yearly_listen_counts():
    return """
        WITH user_listen_counts AS (
            SELECT user_name
                 , count(listened_at) AS listen_count
              FROM listens_of_year
          GROUP BY user_name  
        )
        SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_name, listen_count)
                        )
                    )
                ) AS yearly_listen_counts
          FROM user_listen_counts
    """
