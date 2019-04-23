import listenbrainz_spark

def run_query(query):
    """ Returns dataframe that results from running the query.
    Note: It is the responsibility of the caller to register tables etc.
    """
    return listenbrainz_spark.sql_context.sql(query)