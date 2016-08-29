from __future__ import print_function
import sys
import ujson
from redis import Redis
from time import time, sleep

# For a detailed description of the PubSub Redis mechanism that is being implemented 
# here see this page: https://davidmarquis.wordpress.com/2013/01/03/reliable-delivery-message-queues-with-redis/
# This class is needed, since the PubSub support in Redis is not very robust -- it is quite
# easy for messages to get lost.

# The one change from the solution outlined above is the addition to ref-counts for the JSON
# Each subscriber must decrement the refcount and when the refcount reaches 0, it is responsible
# for removing the JSON and REFCOUNT keys from redis

PUBSUB_NEXTID = ".nextid"
PUBSUB_SUBSCRIBERS = ".subscribers"
PUBSUB_JSON = ".json."                          # append nextid to key
PUBSUB_JSON_REFCOUNT = ".refcount."             # append nextid to key
PUBSUB_SUBSCRIBER_IDS = ".ids."                 # append subscriber name to key
PUBSUB_SUBSCRIBER_IDS_PENDING = ".ids-pending." # append subscriber name to key

WRITE_FAIL_TIMEOUT = 5 # in seconds. 
BATCH_SIZE = 1000      # default size of messages to write
BATCH_TIMEOUT = 3      # in seconds. Don't let a listen get older than this before writing
REQUEST_TIMEOUT = 1    # in seconds. Wait this long to get a listen from redis

class NoSubscribersException(Exception):
    pass

class WriteFailException(Exception):
    pass

class NoSubscriberNameSetException(Exception):
    pass

class RedisPubSubPublisher(object):

    def __init__(self, redis, keyspace_prefix):
        self.prefix = keyspace_prefix
        self.r = redis
        self.subscribers = []


    def get_stats(self):
        stats = {}
        stats['consumers'] = self.r.smembers(self.prefix + PUBSUB_SUBSCRIBERS)
        stats['listens'] = len(self.r.keys(self.prefix + PUBSUB_JSON + "*"))
        stats['refcounts'] = len(self.r.keys(self.prefix + PUBSUB_JSON_REFCOUNT + "*"))
        listen_ids = []
        listen_ids_pending = []
        for consumer in stats['consumers']:
            listen_ids.append("%s: %d" % (consumer, self.r.llen(self.prefix + PUBSUB_SUBSCRIBER_IDS + consumer)))
            listen_ids_pending.append("%s: %d" % (consumer, self.r.llen(self.prefix + PUBSUB_SUBSCRIBER_IDS_PENDING + consumer)))

        stats['num_consumers'] = len(stats['consumers'])
        stats['listen_ids'] = ", ".join(listen_ids)
        stats['listen_ids_pending'] = ", ".join(listen_ids_pending)
        print(stats)

        return stats


    def refresh_subscribers(self):
        """
        Calling this function will refresh the list of subscribers we're going to publish to.
        """
        self.subscribers = []


    def publish(self, message_or_list):
        """
        Call this function to publish a message or a tuple/list of messages to the pub sub.
        """

        if isinstance(message_or_list, (list, tuple)):
            messages = message_or_list
        else:
            messages = (message_or_list)

        p = self.r.pipeline()

        # in order to allow multiple readers of the message stream, we have a set
        # called subscribers. If a subscriber is registered in this set, they *must*
        # consume the messages at some point, otherwise redis will fill up.
        if not self.subscribers:
            self.subscribers = self.r.smembers(self.prefix + PUBSUB_SUBSCRIBERS)

        # If we have no registered subscribers, we can't actually publish messages. Bad!
        if not self.subscribers:
            raise NoSubscribersException

        for message in messages:
            # Each message gets a redis specific ID
            nextid = self.r.incr(self.prefix + PUBSUB_NEXTID)

            # Each message is then inserted into redis using the id from above and a 
            # refcount is set so that we can remove data from redis in a timely fashion
            p.set(self.prefix + PUBSUB_JSON + str(nextid), ujson.dumps(message).encode('utf-8'))
            p.set(self.prefix + PUBSUB_JSON_REFCOUNT + str(nextid), len(self.subscribers))

            # Finally a message id is added a list kept for each subscriber. This way
            # the subscriber can pop message ids from the list and then consume the
            # message. Each subscriber must DECR the corresponding PUBSUB_JSON_REFCOUNT
            # key. If it goes to 0, then the subscriber must remove the PUBSUB_JSON and 
            # PUBSUB_JSON_REFCOUNT keys
            for subscriber in self.subscribers:
                p.lpush(self.prefix + PUBSUB_SUBSCRIBER_IDS + subscriber, nextid)

        # Flush everything we stuffed into the redis pipeline
        p.execute()



class RedisPubSubSubscriber(object):

    def __init__(self, redis, keyspace_prefix):
        self.prefix = keyspace_prefix
        self.subscriber_name = None
        self.r = redis


    def register(self, subscriber_name):
        subscribers = self.r.smembers(self.prefix + PUBSUB_SUBSCRIBERS)
        if not subscriber_name in subscribers:
            self.r.sadd(self.prefix + PUBSUB_SUBSCRIBERS, subscriber_name)
            self.subscriber_name = subscriber_name


    def unregister(self, subscriber_name):
        r.sdel(self.prefix + PUBSUB_SUBSCRIBERS, subscriber_name)
        self.subscriber_name = None


    def subscriber(self, retries=5):
        """
        Subscriber main function which will call write() function to write 
        retrieved messages to the data store.
        """

        if not self.subscriber_name:
            raise NoSubscriberNameSetException

        r = self.r

        # If we have messages on the pending list, lets move them back to the submission list
        ids = r.lrange(self.prefix + PUBSUB_SUBSCRIBER_IDS_PENDING + self.subscriber_name, 0, -1)
        if ids:
            r.lpush(self.prefix + PUBSUB_SUBSCRIBER_IDS + self.subscriber_name, *ids)
            r.ltrim(self.prefix + PUBSUB_SUBSCRIBER_IDS_PENDING + self.subscriber_name, 1, 0)

        # 0 indicates that we've received no messages yet
        batch_start_time = 0 

        messages = []
        message_ids = []

        while True:
            id = self.r.brpoplpush(self.prefix + PUBSUB_SUBSCRIBER_IDS + self.subscriber_name, 
                self.prefix + PUBSUB_SUBSCRIBER_IDS_PENDING + self.subscriber_name, REQUEST_TIMEOUT)

            # If we got an id, fetch the message and add to our list 
            if id:
                # record the time when we get a first message in this batch
                if not batch_start_time:
                    batch_start_time = time()

                message = self.r.get(self.prefix + PUBSUB_JSON + id)
                if message:
                    message_ids.append(id)
                    messages.append(ujson.loads(message))

            if time() - batch_start_time >= BATCH_TIMEOUT:
                break

            if len(messages) >= BATCH_SIZE:
                break
    
        # If we received nothing during our window, return
        if not len(messages):
            return 0

        # We've collected messages to write, now write them
        broken = True
        for i in xrange(retries):
            if self.write(messages):
                broken = False
                break

            sleep(WRITE_FAIL_TIMEOUT)


        # We've tried to write repeatedly, but no luck. :(
        if broken:
            raise WriteFailException

        # Use a pipeline to clean up
        p = r.pipeline()

        # clear the messages-pending list
        p.ltrim(self.prefix + PUBSUB_SUBSCRIBER_IDS_PENDING + self.subscriber_name, 1, 0)

        # now clean up the messages from redis
        for id in message_ids:
            # Get the refcount for this message. If 0, delete it and the refcount
            refcount = p.decr(self.prefix + PUBSUB_JSON_REFCOUNT + id)
            if refcount == 0:
                p.delete(self.prefix + PUBSUB_JSON + id)
                p.delete(self.prefix + PUBSUB_JSON_REFCOUNT + id)

        # Flush everything we stuffed into the redis pipeline
        p.execute()

        return len(messages)

    def write(self, messages):
        """
        This function must be overriden by the derived class!
        If the function was able to correctly write all of the messages, 
        return true. If not, return false. If the function returned false,
        all of the items will be retried at a later time.

        """
        return NotImplemented

