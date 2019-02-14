# coding=utf-8

import ujson
import redis
from time import time
from redis import Redis

from listenbrainz.listen import Listen
from listenbrainz.listenstore import ListenStore

class RedisListenStore(ListenStore):

    RECENT_LISTENS_KEY = "lb_recent_listens"
    RECENT_LISTENS_MAX = 3
    RECENT_LISTENS_MAX_TIME_DIFFERENCE = 300

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


    def update_recent_listens(self, unique):
        """ 
            Store the most recent listens in redis so we can fetch them easily for a recent listens page. This
            is not a critical action, so if it fails, it fails. Let's live with it.
        """

        recent = []
        for listen in unique:
            if  abs(time() - listen['listened_at'].timestamp()) < RECENT_LISTENS_MAX_TIME_DIFFERENCE:
                listen['listened_at'] = listen['listened_at'].timestamp()
                self.log.info(listen)
                recent.append(listen)

        # Don't take this very seriously -- if it fails, really no big deal. Let is go.
        if recent:
            self.redis.rpush(self.RECENT_LISTENS_KEY, *recent)
            self.redis.ltrim(self.RECENT_LISTENS_KEY, -self.RECENT_LISTENS_MAX, -1)


    def get_recent_listens(self, recent, max = RECENT_LISTENS_MAX):
        """
            Get the max number of most recent listens
        """
        return self.redis.lrange(self.RECENT_LISTENS_KEY, 0, max)
