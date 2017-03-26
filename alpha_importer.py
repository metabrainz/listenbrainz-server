from __future__ import print_function, division
from redis import Redis
import config
import requests
from requests.exceptions import HTTPError
import ujson
import time
import sys
import logging
from logging.handlers import RotatingFileHandler
import os
import json

redis_connection = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

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
    for _ in xrange(retries):
        r = requests.post(send_url, headers={'Authorization': 'Token {}'.format(token)}, data = ujson.dumps(data))
        if r.status_code == 200:
            done = True
            break
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
            logger.error(json.dumps(data, indent=4))
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


def import_from_alpha(username, token):
    next_max = int(time.time())
    page_count = 1
    while True:
        try:
            batch = get_batch(username, next_max)
            if batch['payload']['count'] == 0:
                logger.info('All pages done for user {}'.format(username))
                logger.info('Total number of pages done: {}'.format(page_count - 1))
                return
            data = extract_data(batch)
            sent = send_batch(data, token)
            next_max = data['payload'][-1]['listened_at']
            logger.info('Page #{} done.'.format(page_count))
            if sent < len(data['payload']):
                logger.error("Only wrote {} out of {} listens for page {}".format(sent, len(data['payload']), page_count))
            page_count += 1
        except HTTPError as e:
            time.sleep(config.IMPORTER_DELAY)


def queue_pop():
    redis_connection.lpop(config.IMPORTER_QUEUE_KEY)


def update_status(username, status):
    redis_connection.set("{} {}".format(config.IMPORTER_SET_KEY_PREFIX, username), status)


if __name__ == '__main__':
    while True:
        if not queue_empty():
            username, token = queue_front()
            import_from_alpha(username, token)
            queue_pop()
            update_status(username, "DONE")
        else:
            time.sleep(3)
