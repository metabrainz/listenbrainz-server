from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
import os
import logging
from listenbrainz.stats.exceptions import NoCredentialsVariableException, NoCredentialsFileException
import listenbrainz.config as config
import time

JOB_COMPLETION_CHECK_DELAY = 5 # seconds

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

APP_CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

bigquery = None


def init_bigquery_connection():
    """ Initiates the connection to Google BigQuery """

    if not APP_CREDENTIALS_FILE:
        logger.error("The GOOGLE_APPLICATIONS_CREDENTIALS variable is undefined, cannot connect to BigQuery")
        raise NoCredentialsVariableException

    if not os.path.exists(APP_CREDENTIALS_FILE):
        logger.error("The BigQuery credentials file does not exist, cannot connect to BigQuery")
        raise NoCredentialsFileException

    global bigquery
    credentials = GoogleCredentials.get_application_default()
    bigquery = discovery.build('bigquery', 'v2', credentials=credentials)


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
        job = bigquery.jobs().get(projectId=projectId, jobId=jobId).execute(num_retries=5)
        if job["status"]["state"] == "DONE":
            return
        else:
            time.sleep(JOB_COMPLETION_CHECK_DELAY)


def run_query(query, parameters):
    """ Run provided query on Google BigQuery and return the results in the form of a dictionary

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
        "queryParameters": get_parameters_dict(parameters),
        "query": query,
    }

    response = bigquery.jobs().query(
        projectId=config.BIGQUERY_PROJECT_ID,
        body=query_body).execute(num_retries=5)

    job_reference = response['jobReference']

    # Check response to see if query was completed before request timeout.
    # If it wasn't, wait until it has been completed.

    if not response['jobComplete']:
        wait_for_completion(**job_reference)
    else:
        have_results = True

    data = {}
    prev_token = None
    if have_results:
        data['schema'] = response['schema']
        data['rows'] = response['rows']
        try:
            prev_token = response['pageToken']
        except KeyError:
            # if there is no page token, we have all the results
            # so just return the data
            return data
    else:
        query_result = bigquery.jobs().getQueryResults(**job_reference).execute(num_retries=5)
        data['schema'] = query_result['schema']
        data['rows'] = query_result['rows']
        try:
            prev_token = query_result['pageToken']
        except KeyError:
            # if there is no page token, we have all the results
            # so just return the data
            return data

    # keep making requests until we reach the last page and return the data
    # as soon as we do
    while True:
        query_result = bigquery.jobs().getQueryResults(pageToken=prev_token, **job_reference).execute(num_retries=5)
        data['rows'].extend(query_result['rows'])
        try:
            prev_token = query_result['pageToken']
        except KeyError:
            return data
