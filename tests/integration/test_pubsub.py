# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))

import config
import unittest
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException, NoSubscribersException

KEYSPACE = "test"
NUM_POINTS = 100

class Subscriber(RedisPubSubSubscriber):
    def __init__(self, redis, keyspace, name, results):
        RedisPubSubSubscriber.__init__(self, redis, keyspace, __name__)

        self.register(name)
        self.results = results
        self.set_batch_timeout(.1)

    def write(self, dicts):
        self.results.extend(dicts)
        return True

class PubSubTestCase(unittest.TestCase):

    def setUp(self):
        self.results1 = []
        self.results2 = []
        self.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
        self.pub = RedisPubSubPublisher(self.redis, KEYSPACE)
        self.sub1 = Subscriber(self.redis, KEYSPACE, "one", self.results1)
        self.sub2 = Subscriber(self.redis, KEYSPACE, "two", self.results2)

    def test_pubsub(self):

        # publish data points
        for i in xrange(NUM_POINTS):
            self.pub.publish({ 'data' : i })

        # get data points
        for sub in (self.sub1, self.sub2):
            count = 0
            while count < NUM_POINTS:
                count += sub.subscriber()

            self.assertEquals(count, NUM_POINTS)

        # check data points
        for result in (self.results1, self.results2):
            self.assertEquals(len(result), NUM_POINTS)
            if len(result) == NUM_POINTS:
                for i in xrange(NUM_POINTS):
                    self.assertEquals(result[i]['data'], i)
