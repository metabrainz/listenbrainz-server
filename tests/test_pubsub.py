# -*- coding: utf-8 -*-
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

import config
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException, NoSubscribersException

KEYSPACE = "test"

class PubSubTestCase(RedisPubSubSubscriber):

    def setUp(self):
        self.redis = Redis(config.REDIS_HOST)
        self.pub = RedisPubSubPublisher(self.redis, KEYSPACE)
        self.sub = RedisPubSubSubscriber(self.redis, KEYSPACE)
        self.assertIsNotNone(self.pub)
        self.assertIsNotNone(self.sub)

    def test_insert(self):
        self.pub.publish({ 'data' : 'we haz it' })
