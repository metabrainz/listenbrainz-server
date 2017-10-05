import os
from googleapiclient import discovery
import googleapiclient
from oauth2client.client import GoogleCredentials

APP_CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

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


# Exceptions
class BigQueryException(Exception):
    pass


class NoCredentialsVariableException(BigQueryException):
    pass


class NoCredentialsFileException(BigQueryException):
    pass
