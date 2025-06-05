def get_feedback_cache_query(with_filter: bool = False):
    """ Import feedback data from postgres to HDFS.

        If with_filter is True, the query is prepared in a way such that it can be filtered using a list of
        recording mbids passed as a VALUES list.
    """
    cte_clause = ""
    mbid_filter_clause = ""
    if with_filter:
        cte_clause = "WITH mbids (mbid) AS (VALUES %s)"
        mbid_filter_clause = "JOIN mbids m ON m.mbid = recording_mbid"

    return f"""
        {cte_clause}
        SELECT user_id
             , recording_mbid::text
             , score AS feedback
          FROM recording_feedback
        {mbid_filter_clause}
    """
