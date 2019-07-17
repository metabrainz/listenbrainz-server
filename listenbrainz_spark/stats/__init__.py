from datetime import datetime
from dateutil.relativedelta import relativedelta

import listenbrainz_spark
from listenbrainz_spark.exceptions import SQLException

from pyspark.sql.utils import *

def run_query(query):
    """ Returns dataframe that results from running the query.

        Args:
            query (str): SQL query to execute.

    Note:
        >> While dealing with SQL queries in pyspark, catch the outermost exceptions and not Py4JJavaError
           since it is the innermost exception raised. For all the final(outer) exceptions refer to:
           'https://github.com/apache/spark/blob/master/python/pyspark/sql/utils.py'.
           In all other cases where Py4JJavaError is the only exception raised, catch it as such.
        >> It is the responsibility of the caller to register tables etc.
    """
    try:
        processed_query = listenbrainz_spark.sql_context.sql(query)
    except AnalysisException as err:
        raise SQLException('{}. Failed to analyze SQL query plan for\n{}\n{}'.format(type(err).__name__, query, str(err)))
    except ParseException as err:
        raise SQLException('{}. Failed to parse SQL command\n{}\n{}'.format(type(err).__name__, query, str(err)))
    except IllegalArgumentException as err:
        raise SQLException('{}. Passed an illegal or inappropriate argument to\n{}\n{}'.format(type(err).__name__, query,
            str(err)))
    except StreamingQueryException as err:
        raise SQLException('{}. Exception that stopped a :class:`StreamingQuery`\n{}\n{}'.format(type(err).__name__, query,
            str(err)))
    except QueryExecutionException as err:
        raise SQLException('{}. Failed to execute a query{}\n{}'.format(type(err).__name__, query, str(err)))
    except UnknownException as err:
        raise SQLException('{}. An error occurred while executing{}\n{}'.format(type(err).__name__, query, str(err)))
    return processed_query

def adjusted_date(months):
    t = datetime.utcnow().replace(day=1)
    date = t + relativedelta(months=months)
    return date
