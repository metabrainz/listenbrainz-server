from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
import os
import logging
from listenbrainz.stats.exceptions import NoCredentialsVariableException, NoCredentialsFileException

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
