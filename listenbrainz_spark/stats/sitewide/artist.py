from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_artists(table: str, date_format: str):
    """ Get artist information (artist_name, artist_msid etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: Name of the temporary table.
            date_format: Format in which the listened_at field should be formatted.

        Returns:
            iterator (iter): An iterator over result
    """

    # Format the listened_at field according to the provided date_format string
    formatted_listens = run_query(f"""
                SELECT artist_name
                     , artist_credit_id
                     , date_format(listened_at, '{date_format}') as listened_at
                  FROM {table}
            """)
    formatted_listens.createOrReplaceTempView('listens')

    result = run_query("""
                SELECT listens.artist_name
                     , listens.artist_credit_id
                     , time_range.time_range
                     , time_range.from_ts
                     , time_range.to_ts
                     , count(*) as listen_count
                  FROM listens
                  JOIN time_range
                    ON listens.listened_at == time_range.time_range
              GROUP BY listens.artist_name
                     , listens.artist_credit_id
                     , time_range.time_range
                     , time_range.from_ts
                     , time_range.to_ts
              """)

    iterator = result \
        .withColumn("artists", struct("listen_count", "artist_name", "artist_credit_id")) \
        .groupBy("time_range", "from_ts", "to_ts") \
        .agg(sort_array(collect_list("artists"), asc=False).alias("artists")) \
        .toLocalIterator()

    return iterator
