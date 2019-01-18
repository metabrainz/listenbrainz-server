# coding=utf-8

import ujson
import redis
import time
from redis import Redis

from listenbrainz.listen import Listen
from listenbrainz.listenstore import ListenStore

class RedisListenStore(ListenStore):
    def __init__(self, log, conf):
        super(RedisListenStore, self).__init__(log)
        self.log.info('Connecting to redis: %s:%s', conf['REDIS_HOST'], conf['REDIS_PORT'])
        self.redis = Redis(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'], decode_responses=True)

    def get_playing_now(self, user_id):
        """ Return the current playing song of the user

            Arguments:
                user_id (int): the id of the user in the db

            Returns:
                Listen object which is the currently playing song of the user

        """
        data = self.redis.get('playing_now:{}'.format(user_id))
        if not data:
            return None
        data = ujson.loads(data)
        data.update({'playing_now': True})
        return Listen.from_json(data)

    def put_playing_now(self, user_id, listen, expire_time):
        """ Save a listen as `playing_now` for a particular time in Redis.

        Args:
            user_id (int): the row ID of the user
            listen (dict): the listen data
            expire_time (int): the time in seconds in which the `playing_now` listen should expire
        """
        self.redis.setex(
            'playing_now:{}'.format(user_id),
            ujson.dumps(listen).encode('utf-8'),
            expire_time,
        )

    def check_connection(self):
        """ Pings the redis server to check if the connection works or not """
        try:
            self.redis.ping()
        except redis.exceptions.ConnectionError as e:
            self.log.error("Redis ping didn't work: {}".format(str(e)))
            raise
