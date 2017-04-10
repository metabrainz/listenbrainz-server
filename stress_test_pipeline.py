from __future__ import print_function
import random
import requests
import threading
import uuid
import argparse
import string
import json
import time
import sys
import os
import config
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException, NoSubscribersException

TIMESTAMP_LOW = 946684800   # unix timestamp of 01/01/2000
TIMESTAMP_HIGH = 1491004800 # unix timestamp of 01/04/2017

# Define the values for types of listens
LISTEN_TYPE_SINGLE = 1
LISTEN_TYPE_IMPORT = 2
LISTEN_TYPE_PLAYING_NOW = 3

# PubSub Keyspace
LISTEN_KEYSPACE = "ilisten"  # for incoming listens

class StressTester(object):

    def __init__(self, listen_count, batch_size):
        self.listen_count = listen_count
        self.batch_size = batch_size
        self.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

    def random_timestamp(self):
        """
        Returns a random timestamp between TIMESTAMP_LOW and TIMESTAMP_HIGH
        """
        return int(TIMESTAMP_LOW + (TIMESTAMP_HIGH - TIMESTAMP_LOW) * random.random())

    def random_string(self):
        """
        Returns a random string containing uppercase and lowercase ascii characters and digits
        """
        # random length b/w 1 and 50
        l = random.randint(1, 50)
        s = ''
        for _ in range(l):
            s += random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        return s

    def random_listen(self, user_name, count=1):
        """
        Generates random listen data
        """

        listens= []
        for i in xrange(count):
            listens.append( 
                    {
                    'listened_at': self.random_timestamp(),
                    'user_id' : user_name,
                    'user_name' : user_name,
                    'track_metadata': {
                        'artist_name': self.random_string(),
                        'track_name': self.random_string(),
                        'release_name': self.random_string(),
                        'additional_info': {
                            'random_data': self.random_string(),
                        }
                    }
                })

        return listens

    def stress_test(self):
        pubsub = RedisPubSubPublisher(self.redis, LISTEN_KEYSPACE)
        batches = self.listen_count / self.batch_size
        for batch in range(batches):
            submit = self.random_listen(self.random_string(), self.batch_size)
            try:
                pubsub.publish(submit)
            except NoSubscribersException:
                print("Cannot submit listens to pipeline")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--listencount", dest="listen_count", type=int, help="specify the number of listens to send while testing")
    parser.add_argument("-b", "--batchsize", dest="batch_size", type=int, help="specify the number of listens per submission")
    args = parser.parse_args()
    if not args.listen_count or not args.batch_size:
        print("Please provide all options required, see -h for help")
        sys.exit(-1)

    st = StressTester(args.listen_count, args.batch_size)
    st.stress_test()
