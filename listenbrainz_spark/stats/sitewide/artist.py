from listenbrainz_spark.path import MBID_MSID_MAPPING
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS
from pyspark.sql.functions import collect_list, sort_array, struct


def get_artists(table: str, date_format: str, use_mapping: bool):
    """ Get artist information (artist_name, artist_msid etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: Name of the temporary table.
            date_format: Format in which the listened_at field should be formatted.
            use_mapping: Flag to optionally use the mapping step to improve the results

        Returns:
            iterator (iter): An iterator over result
                    {
                        time_range_1: [{
                            'artist_name': str,
                            'artist_msid': str,
                            'artist_mbids': list(str),
                            'listen_count': int
                        }],
                        time_range_2: [{...}],
                    }
    """

    # Format the listened_at field according to the provided date_format string
    formatted_listens = run_query("""
                SELECT artist_name
                     , artist_msid
                     , artist_mbids
                     , date_format(listened_at, '{date_format}') as listened_at
                  FROM {table}
            """.format(table=table, date_format=date_format))
    formatted_listens.createOrReplaceTempView('listens')

    # Use MSID-MBID mapping to improve results
    if use_mapping:
        mapped_df = _create_mapped_dataframe()
        mapped_df.createOrReplaceTempView('listens')

    result = run_query("""
                SELECT listens.artist_name
                     , listens.artist_msid
                     , listens.artist_mbids
                     , time_range.time_range
                     , count(*) as listen_count
                  FROM listens
                  JOIN time_range
                    ON listens.listened_at == time_range.time_range
              GROUP BY listens.artist_name
                     , listens.artist_msid
                     , listens.artist_mbids
                     , time_range.time_range
              """)

    iterator = result \
        .withColumn("artists", struct("listen_count", "artist_name", "artist_msid", "artist_mbids")) \
        .groupBy("time_range") \
        .agg(sort_array(collect_list("artists"), asc=False).alias("artists")) \
        .toLocalIterator()

    return iterator


def _create_mapped_dataframe():
    """ Use MSID-MBID mapping to improve the data accuracy and quality

        Returns:
            mapped_df (dataframe): A DataFrame with mapped data
    """
    # Read the mapped data into dataframe with the needed columns
    mapping_df = read_files_from_HDFS(MBID_MSID_MAPPING).select('mb_artist_credit_name',
                                                                'mb_artist_credit_mbids',
                                                                'msb_artist_msid')
    mapping_df.createOrReplaceTempView('mapping')

    mapped_df = run_query("""
                SELECT CASE
                         WHEN isnull(mb_artist_credit_name) THEN artist_name
                         ELSE mb_artist_credit_name
                       END as artist_name
                     , CASE
                         WHEN isnull(mb_artist_credit_mbids) THEN artist_mbids
                         ELSE mb_artist_credit_mbids
                       END as artist_mbids
                     , CASE
                         WHEN isnull(mb_artist_credit_mbids) AND cardinality(artist_mbids) == 0 THEN nullif(artist_msid, "")
                         ELSE NULL
                       END as artist_msid
                     , listened_at
                  FROM listens
             LEFT JOIN mapping
                    ON listens.artist_msid == mapping.msb_artist_msid
                    """)

    return mapped_df
