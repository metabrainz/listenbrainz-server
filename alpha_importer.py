from __future__ import print_function
from redis import Redis
import config
import requests
import ujson
import time
import sys

redis_connection = Redis(host = config.REDIS_HOST)
QUEUE_KEY = 'alphaimporter:queue'
SET_KEY_PREFIX = 'alphaimporter:set'
ALPHA_URL = 'https://api.listenbrainz.org/'
BETA_URL = 'http://0.0.0.0:3031'
LISTENS_PER_GET = 100

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
        print("get from alpha http response code: {}".format(r.status_code), file = sys.stderr)
        return None


def get_data(batch):
    data = {'listen_type':'import', 'payload': []}
    for listen in batch['payload']['listens']:
        data['payload'].append(listen)
    return data


def send_batch(data, token):
    send_url = '{}/1/submit-listens'.format(BETA_URL)
    r = requests.post(send_url, headers = {'Authorization': 'Token {}'.format(token)}, data = ujson.dumps(data))
    if r.status_code == 200:
        return 1
    else:
        print("submission to beta returned response code: {}".format(r.status_code), file = sys.stderr)
        return 0


def import_from_alpha(username, token):
    next_max = int(time.time())
    cnt = 1
    while True:
        batch = get_batch(username, next_max)
        if not batch: # if get_batch doesn't return data, we try again
            continue
        if batch['payload']['count'] == 0:
            print("All pages done")
            print("total number of pages = {}".format(cnt))
            return 1
        data = get_data(batch)
        sent = send_batch(data, token)
        if sent:
            next_max = data['payload'][-1]['listened_at']
            print("page #{} done".format(cnt))
            cnt += 1

def queue_pop():
    redis_connection.lpop(QUEUE_KEY)


def set_remove(username):
    redis_connection.delete("{} {}".format(SET_KEY_PREFIX, username))

if __name__ == '__main__':
    while not queue_empty():
        username, token = queue_front()
        done = import_from_alpha(username, token)
        if done:
            queue_pop()
            set_remove(username)
