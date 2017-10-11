
from redis import Redis
from listenbrainz import config
import requests
from requests.exceptions import HTTPError
import ujson
import time
import sys
import logging
from logging.handlers import RotatingFileHandler
from listenbrainz.listenstore import InfluxListenStore
import redis

redis_connection = None

LATEST_IMPORT_ENDPOINT = '{root_url}/1/latest-import'.format(root_url=config.BETA_URL)

# create a logger to log messages into LOG_FILE
logger = logging.getLogger('alpha_importer')
logger.setLevel(logging.DEBUG)

if config.IMPORTER_LOG_FILE == "-":
    handler = logging.StreamHandler(sys.stdout)
else:
    handler = RotatingFileHandler(config.IMPORTER_LOG_FILE, maxBytes=512 * 1024, backupCount=100)

handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def init_redis_connection():
    """ Initiates the connection to Redis """

    global redis_connection
    while True:
        try:
            redis_connection = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            redis_connection.ping()
            return
        except redis.exceptions.ConnectionError as e:
            logger.error("Couldn't connect to redis: {}:{}".format(config.REDIS_HOST, config.REDIS_PORT))
            logger.error("Sleeping for 2 seconds and trying again...")
            time.sleep(2)


def queue_empty():
    return redis_connection.llen(config.IMPORTER_QUEUE_KEY) == 0


def queue_front():
    # get the first element from queue and split it to get username and auth_token
    token, username = redis_connection.lindex(config.IMPORTER_QUEUE_KEY, 0).split(" ", 1)
    return username, token


def get_batch(username, max_ts):
    get_url = '{}/1/user/{}/listens'.format(config.ALPHA_URL, username)
    payload = {"max_ts": max_ts, "count": config.LISTENS_PER_GET}
    r = requests.get(get_url, params = payload)
    if r.status_code == 200:
        return ujson.loads(r.text)
    else:
        logger.error("GET from alpha HTTP response code: {}".format(r.status_code))
        raise HTTPError


def extract_data(batch):
    data = {'listen_type':'import', 'payload': []}
    for listen in batch['payload']['listens']:
        if 'recording_msid' in listen:
            del listen['recording_msid']
        if  'release_msid' in listen['track_metadata']['additional_info']:
            del listen['track_metadata']['additional_info']['release_msid']
        if 'artist_msid' in listen['track_metadata']['additional_info']:
            del listen['track_metadata']['additional_info']['artist_msid']
        data['payload'].append(listen)
    return data


class BetaAuthorizationException(Exception):
    pass


def send_batch(data, token, retries=5):
    """
    Sends a batch of data. If fails, then breaks the data into two parts and
    recursively tries to send them, until we find the culprit listen

    Returns: number of listens successfully sent
    """

    if not data['payload']:
        return 0

    send_url = '{}/1/submit-listens'.format(config.BETA_URL)
    done = False
    for _ in range(retries):
        r = requests.post(send_url, headers={'Authorization': 'Token {}'.format(token)}, data = ujson.dumps(data))
        if r.status_code == 200:
            done = True
            break
        elif r.status_code == 401 and r.json()['error'] == 'Invalid authorization token.':
            logger.error('Invalid auth token according to beta, not going to retry now.')
            raise BetaAuthorizationException
        else:
            time.sleep(config.IMPORTER_DELAY)

    if done:
        return len(data['payload'])
    elif not done and len(data['payload']) == 1:
        # try to send the bad listen one more time and if it doesn't work
        # log the error
        r = requests.post(send_url, headers={'Authorization': 'Token {}'.format(token)}, data = ujson.dumps(data))
        if r.status_code == 200:
            return 1
        else:
            logger.error("Unable to submit bad listen to beta:")
            logger.error(ujson.dumps(data))
            logger.error("Response code from beta: {}".format(r.status_code))
            logger.error(r.text)
            return 0
    else:
        slice_index = len(data['payload']) // 2
        # send first half
        half_data = {
            'listen_type': 'import',
            'payload': data['payload'][slice_index :],
        }
        sent = send_batch(half_data, token, retries)
        # send second half
        half_data['payload'] = data['payload'][: slice_index]
        sent += send_batch(half_data, token, retries)
        return sent

def get_latest_import_time(username):
    """ Send a GET request to the ListenBrainz Beta server to get the latest import time
        from previous imports for the user.
    """
    response = requests.get(
        LATEST_IMPORT_ENDPOINT,
        params={
            'user_name': username
        }
    )
    if response.status_code == 200:
        return int(ujson.loads(response.text)['latest_import'])
    else:
        raise HTTPError

def update_latest_import_time(token, ts):
    """ Send a POST request to the ListenBrainz server after the import is complete to
        update the latest import time on the server. This will make future imports stop
        when they reach this point of time in the listen history.
    """

    response = requests.post(
        LATEST_IMPORT_ENDPOINT,
        headers={'Authorization': 'Token {user_token}'.format(user_token=token)},
        data=ujson.dumps({'ts': ts})
    )
    if response.status_code != 200:
        raise HTTPError


def import_from_alpha(username, token):
    """ Function to import listens from alpha for user with given username """

    logger.info('Beginning alpha import for %s' % username)

    # first get the timestamp until which previous imports have already added data
    latest_import_ts = get_latest_import_time(username)

    next_max = int(time.time()) # variable used for pagination
    page_count = 1

    # we'll send this to LB Beta at the end of the import
    newest_timestamp_imported_this_time = 0

    stop = False
    while True:
        try:
            if stop:
                update_latest_import_time(token, newest_timestamp_imported_this_time)
                logger.info('All pages done for user {}'.format(username))
                logger.info('Total number of pages done: {}'.format(page_count - 1))
                return

            batch = get_batch(username, next_max)

            # if this is the last page or if this is the page upto which we had imported earlier, then stop
            if batch['payload']['count'] == 0 or batch['payload']['listens'][-1]['listened_at'] < latest_import_ts:
                stop = True

            # if this is the first page, then  get the value with which we'll update latest_update on LB
            if page_count == 1 and batch['payload']['count'] > 0:
                newest_timestamp_imported_this_time = batch['payload']['listens'][0]['listened_at']

            # send the current batch of data
            data = extract_data(batch)
            sent = send_batch(data, token)

            # if we have more pages to get, get the timestamp
            # of the last listen in this list
            if not stop:
                next_max = data['payload'][-1]['listened_at']

            page_count += 1
        except HTTPError as e:
            time.sleep(config.IMPORTER_DELAY)

        except BetaAuthorizationException:
            logger.error('Invalid authorization token for user %s', username)
            logger.info('Stopping alpha import for user %s', username)
            return


def queue_pop():
    redis_connection.lpop(config.IMPORTER_QUEUE_KEY)


def update_status(username, status):
    redis_connection.set("{} {}".format(config.IMPORTER_SET_KEY_PREFIX, username), status)


def init_influx_connection():
    """ Connects to influx and returns an InfluxListenStore instance """
    while True:
        try:
            return InfluxListenStore({
                'REDIS_HOST': config.REDIS_HOST,
                'REDIS_PORT': config.REDIS_PORT,
                'INFLUX_HOST': config.INFLUX_HOST,
                'INFLUX_PORT': config.INFLUX_PORT,
                'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
            })
        except Exception as e:
            logger.error("Couldn't create InfluxListenStore instance: {}".format(str(e)))
            logger.error("Sleeping 2 seconds and then retrying...")
            time.sleep(2)


if __name__ == '__main__':
    init_redis_connection()
    db_connection = init_influx_connection()
    logger.info("alpha_importer started")
    while True:
        if not queue_empty():
            username, token = queue_front()
            import_from_alpha(username, token)
            queue_pop()
            update_status(username, "DONE")
            db_connection.reset_listen_count(username)
        else:
            time.sleep(3)
