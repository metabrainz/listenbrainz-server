import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_listen_count(year):
    setup_listens_for_year(year)
    data = run_query(_get_yearly_listen_counts()).collect()
    yield {
        "type": "year_in_music_listen_count",
        "data": data[0]["_get_yearly_listen_counts"]
    }


def _get_yearly_listen_counts():
    return """
        SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_name, count(listened_at))
                        )
                    )
                ) AS yearly_listen_counts
          FROM listens_of_year
      GROUP BY user_name  
    """
