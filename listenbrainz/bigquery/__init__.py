import googleapiclient
import logging
import os
import time

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from listenbrainz import config
from oauth2client.client import GoogleCredentials

APP_CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
JOB_COMPLETION_CHECK_DELAY = 5
DML_STREAMING_ROWS_DELAY = 30

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_bigquery_object():
    """ Initiates the connection to Google BigQuery. Returns a BigQuery object. """

    if not APP_CREDENTIALS_FILE:
        logger.error("The GOOGLE_APPLICATIONS_CREDENTIALS variable is undefined, cannot connect to BigQuery")
        raise NoCredentialsVariableException

    if not os.path.exists(APP_CREDENTIALS_FILE):
        logger.error("The BigQuery credentials file does not exist, cannot connect to BigQuery")
        raise NoCredentialsFileException

    credentials = GoogleCredentials.get_application_default()
    return discovery.build('bigquery', 'v2', credentials=credentials)


def get_parameters_dict(parameters):
    """ Converts a list of parameters to be passed to BigQuery into the standard format that the API requires.
        The format can be seen here:
        https://developers.google.com/resources/api-libraries/documentation/bigquery/v2/python/latest/bigquery_v2.jobs.html#query

        Args: parameters: a list of dictionaries of the following form
                {
                    "name" (str): name of the parameter,
                    "type" (str): type of the parameter,
                    "value" (str): value of the parameter
                }

        Returns: A list of dictionaries that can be passed to the API call
    """

    bq_params = []
    for param in parameters:
        # construct parameter dict
        temp = {}
        temp["name"] = param["name"]
        temp["parameterType"] = {
            "type": param["type"],
        }
        temp["parameterValue"] = {
            "value": param["value"],
        }

        # append parameter dict to main list
        bq_params.append(temp)

    return bq_params


def wait_for_completion(projectId, jobId):
    """ Make requests periodically until the passed job has been completed """

    while True:

        try:
            job = bigquery.jobs().get(projectId=projectId, jobId=jobId).execute(num_retries=5)
        except googleapiclient.errors.HttpError as err:
            logger.error("HttpError while waiting for completion of job: {}".format(err))
            time.sleep(JOB_COMPLETION_CHECK_DELAY)
            continue

        if job["status"]["state"] == "DONE":
            return
        else:
            time.sleep(JOB_COMPLETION_CHECK_DELAY)


def format_results(data):
    """ The data returned by BigQuery contains a dict for the schema and a seperate dict for
        the rows. This function formats the data into a form similar to the data returned
        by sqlalchemy i.e. a dictionary keyed by row names
    """

    formatted_data = []
    for row in data['rows']:
        formatted_row = {}
        for index, val in enumerate(row['f']):
            formatted_row[data['schema']['fields'][index]['name']] = val['v']
        formatted_data.append(formatted_row)
    return formatted_data


def run_query(bigquery, query, parameters=None, dml=False):
    """ Run provided query on Google BigQuery and return the results in the form of a dictionary

        Args:
            bigquery: the bigquery connection object
            query: the BigQuery standard SQL query (not legacy SQL)
            parameters: the parameters to be passed to the query
            dml: a flag which specifies whether the query is a DML (insert, update, delete) query
                or not

        Note: This is a synchronous action
    """

    # Run the query
    query_body = {
        "kind": "bigquery#queryRequest",
        "parameterMode": "NAMED",
        "default_dataset": {
            "projectId": config.BIGQUERY_PROJECT_ID,
            "datasetId": config.BIGQUERY_DATASET_ID,
        },
        "useLegacySql": False,
        "queryParameters": get_parameters_dict(parameters) if parameters else [],
        "query": query,
    }

    while True:
        try:
            response = bigquery.jobs().query(
                projectId=config.BIGQUERY_PROJECT_ID,
                body=query_body).execute(num_retries=5)
            break
        except HttpError as e:
            # BigQuery does not allow deletion of rows which may be
            # in the streaming buffer, so if an error is returned
            # because of that, sleep and try again.
            logger.error(str(e))
            if dml and '400' in str(e):
                time.sleep(DML_STREAMING_ROWS_DELAY)
            else:
                raise

    job_reference = response['jobReference']

    # Check response to see if query was completed before request timeout.
    # If it wasn't, wait until it has been completed.

    if not response['jobComplete']:
        wait_for_completion(**job_reference)
    else:
        have_results = True

    # if this is a dml query then we don't need results.
    if dml:
        return

    data = {}
    prev_token = None
    if have_results:
        first_page = response
    else:
        while True:
            try:
                first_page = bigquery.jobs().getQueryResults(**job_reference).execute(num_retries=5)
                break
            except googleapiclient.errors.HttpError as err:
                logger.error("HttpError when getting first page after completion of job: {}".format(err))
                time.sleep(JOB_COMPLETION_CHECK_DELAY)


    data['schema'] = first_page['schema']
    data['rows']   = first_page['rows']
    try:
        prev_token = first_page['pageToken']
    except KeyError:
        # if there is no page token, we have all the results
        # so just return the data
        return format_results(data)

    # keep making requests until we reach the last page and return the data
    # as soon as we do
    while True:
        try:
            query_result = bigquery.jobs().getQueryResults(pageToken=prev_token, **job_reference).execute(num_retries=5)
        except googleapiclient.errors.HttpError as err:
            logger.error("HttpError when getting query results: {}".format(err))
            continue

        data['rows'].extend(query_result['rows'])
        try:
            prev_token = query_result['pageToken']
        except KeyError:
            return format_results(data)


def _load_fields():
    """ returns the fields in the listenbrainz google bigquery schema
    """
    schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'bigquery')
    with open(os.path.join(schema_dir, 'listen-schema.json')) as f:
        return json.load(f)


def create_bigquery_table(bigquery, table_name, force=False):
    """ create a table with specified name in google bigquery.
    """
    try:
        result = bigquery.tables().get(
            projectId=config.BIGQUERY_PROJECT_ID,
            datasetId=config.BIGQUERY_DATASET_ID,
            tableId=table_name,
        ).execute(num_retries=5)
        if 'creationTime' in result:
            print('Table %s already present in BigQuery...' % table_name)
            if force:
                print('Deleting table...')
                bigquery.tables().delete(
                    projectId=config.BIGQUERY_PROJECT_ID,
                    datasetId=config.BIGQUERY_DATASET_ID,
                    tableId=table_name,
                ).execute(num_retries=5)
            else:
                print('Moving ahead...')
                return
    except googleapiclient.errors.HttpError as e:
        if e.resp.status != 404:
            print('Error while getting information for table %s...' % table_name)
            raise

    creation_request_body = {
        'tableReference': {
            'projectId': config.BIGQUERY_PROJECT_ID,
            'datasetId': config.BIGQUERY_DATASET_ID,
            'tableId': table_name,
        },
        'schema': {
            'fields': _load_fields()
        },
    }

    response = bigquery.tables().insert(
        projectId=config.BIGQUERY_PROJECT_ID,
        datasetId=config.BIGQUERY_DATASET_ID,
        body=creation_request_body,
    ).execute(num_retries=5)
    print('Table %s created!' % table_name)


def get_list_of_tables(bigquery, project_id, dataset_id, log=print):
    """ Returns all table names present in specified BigQuery dataset.

    Args:
        bigquery: bigquery object created via listenbrainz.bigquery.create_bigquery_object
        project_id (str): the name of the BigQuery project
        dataset_id (str): the name of the BigQuery dataset
        log: the function to use to log errors

    Returns:
        A dict containing each table present in the dataset as a key
        (using dict for fast lookup)
    """
    try:
        data = bigquery.tables().list(
            projectId=project_id,
            datasetId=dataset_id,
        ).execute(num_retries=5)
    except HttpError as e:
        log('Error while retrieving table names from bigquery: %s' % str(e))
        raise

    table_names = {}
    for table in data['tables']:
        table_name = table['tableReference']['tableId']
        table_names[table_name] = 1

    return table_names


# Exceptions
class BigQueryException(Exception):
    pass


class NoCredentialsVariableException(BigQueryException):
    pass


class NoCredentialsFileException(BigQueryException):
    pass
