from listenbrainz_spark.year_in_music.utils import setup_listens_for_year, setup_all_releases
from listenbrainz_spark.stats import run_query


def get_most_listened_year(year):
    setup_listens_for_year(year)
    setup_all_releases()
    data = run_query(_get_releases_with_date()).collect()
    yield {
        "type": "most_listened_year",
        "year": year,
        "data": data[0]["all_user_yearly_counts"]
    }


def _get_releases_with_date():
    return """
        WITH release_date AS (
            SELECT title
                 , id AS release_mbid
                 , int(substr(`release-group`.`first-release-date`, 1, 4)) AS year
              FROM release
             WHERE substr(`release-group`.`first-release-date`, 1, 4) != '????'
               AND substr(`release-group`.`first-release-date`, 1, 4) != ''
        ), listen_year AS (
        SELECT user_id
             , collect_list(release_date.release_mbid) AS release_mbids
             , release_date.year
             , count(*) AS listen_count
          FROM listens_of_year l
          JOIN release_date
            ON l.release_mbid = release_date.release_mbid
      GROUP BY user_id
             , release_date.year
        ), grouped_counts AS (
        SELECT user_id
             , map_from_entries(
                     collect_list(
                         struct(year, listen_count)
                     )
               ) AS yearly_count
          FROM listen_year
      GROUP BY user_id
        )
        SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_id, yearly_count)
                        )
                    )
               ) AS all_user_yearly_counts
          FROM grouped_counts
    """
