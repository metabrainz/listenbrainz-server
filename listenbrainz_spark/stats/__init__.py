import listenbrainz_spark
from datetime import datetime
from dateutil.relativedelta import relativedelta

def run_query(query):
    """ Returns dataframe that results from running the query.

    Note: It is the responsibility of the caller to register tables etc.
    """
    return listenbrainz_spark.sql_context.sql(query)

def date_for_stats_calculation():
    t = datetime.utcnow().replace(day=1)
    date = t + relativedelta(months=-1)
    return date
