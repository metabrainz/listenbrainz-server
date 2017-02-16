from __future__ import print_function
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

redis_connection = Redis(host = config.REDIS_HOST)
QUEUE_KEY = 'alphaimporter:queue'
SET_KEY_PREFIX = 'alphaimporter:set'
ALPHA_URL = 'https://alpha.listenbrainz.org/'
BETA_URL = 'https://listenbrainz.org'
LISTENS_PER_GET = 100
LOG_FILE = os.path.join(os.getcwd(), 'alpha_importer.log')
DELAY = 3 # delay if requests don't return http 200

# create a logger to log messages into LOG_FILE
logger = logging.getLogger('alpha_importer')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG_FILE, maxBytes = 512 * 1024, backupCount = 100)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def queue_empty():
    return redis_connection.llen(QUEUE_KEY) == 0


def queue_front():
    # get the first element from queue and split it to get username and auth_token
    username, token = redis_connection.lindex(QUEUE_KEY, 0).split()
    return username, token


def get_batch(username, max_ts):
    get_url = '{}/1/user/{}/listens'.format(ALPHA_URL, username)
    payload = {"max_ts": max_ts, "count": LISTENS_PER_GET}
    r = requests.get(get_url, params = payload)
    if r.status_code == 200:
        return ujson.loads(r.text)
    else:
        logger.error("get from alpha http response code: {}".format(r.status_code))
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


def send_batch(data, token):
    send_url = '{}/1/submit-listens'.format(BETA_URL)
    r = requests.post(send_url, headers = {'Authorization': 'Token {}'.format(token)}, data = ujson.dumps(data))
    if r.status_code != 200:
        logger.error("submission to beta returned response code: {}".format(r.status_code))
        raise HTTPError


def import_from_alpha(username, token):
    next_max = int(time.time())
    page_count = 1
    while True:
        try:
            batch = get_batch(username, next_max)
            if batch['payload']['count'] == 0:
                logger.info('All pages done for user {}'.format(username))
                logger.info('Total number of pages done: {}'.format(page_count))
                return True
            data = extract_data(batch)
            sent = send_batch(data, token)
            next_max = data['payload'][-1]['listened_at']
            logger.info('Page #{} done.'.format(page_count))
            page_count += 1
        except HTTPError:
            time.sleep(DELAY)


def queue_pop():
    redis_connection.lpop(QUEUE_KEY)


def update_status(username, status):
    redis_connection.set("{} {}".format(SET_KEY_PREFIX, username), status)


if __name__ == '__main__':
    while True:
        if not queue_empty():
            username, token = queue_front()
            if import_from_alpha(username, token):
                queue_pop()
                update_status(username, "DONE")
