# coding=utf-8


import ujson

import redis
from redis import Redis

from listenbrainz.listen import Listen
from listenbrainz.listenstore import ListenStore, MIN_ID


class RedisListenStore(ListenStore):
    def __init__(self, conf):
        ListenStore.__init__(self, conf)
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
        data.update({'listened_at': MIN_ID+1})
        return Listen.from_json(data)

    def check_connection(self):
        """ Pings the redis server to check if the connection works or not """
        try:
            self.redis.ping()
        except redis.exceptions.ConnectionError as e:
            self.log.error("Redis ping didn't work: {}".format(str(e)))
            raise

    def store_latest_listens(self, listens):
        try:
            all_listens = self.redis.set('latest_listens', listens)
        except redis.exceptions.ConnectionError as e:
            self.log.error("The data can't be set due to: {}".format(str(e)))

    def get_latest_listens(self):
        """ This module is used to get the datas that has been set in the redis
            Please use this function instead of store_latest_listens
        """
        return self.redis.get('latest_listens')

