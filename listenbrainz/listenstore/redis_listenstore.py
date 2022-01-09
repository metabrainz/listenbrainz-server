from datetime import datetime
from typing import Optional

import redis
import ujson
from brainzutils import cache

from listenbrainz.listen import Listen, NowPlayingListen
from listenbrainz.listenstore import ListenStore


class RedisListenStore(ListenStore):

    RECENT_LISTENS_KEY = "rl-"
    RECENT_LISTENS_MAX = 100
    PLAYING_NOW_KEY = "pn."
    LISTEN_COUNT_PER_DAY_EXPIRY_TIME = 3 * 24 * 60 * 60  # 3 days in seconds
    LISTEN_COUNT_PER_DAY_KEY = "lc-day-"

    def get_playing_now(self, user_id):
        """ Return the current playing song of the user

            Arguments:
                user_id (int): the id of the user in the db

            Returns:
                Listen object which is the currently playing song of the user

        """
        data = cache.get(self.PLAYING_NOW_KEY + str(user_id))
        if not data:
            return None
        data = ujson.loads(data)
        return NowPlayingListen(user_id=data['user_id'], user_name=data['user_name'], data=data['track_metadata'])

    def put_playing_now(self, user_id, listen, expire_time):
        """ Save a listen as `playing_now` for a particular time in Redis.

        Args:
            user_id (int): the row ID of the user
            listen (dict): the listen data
            expire_time (int): the time in seconds in which the `playing_now` listen should expire
        """
        cache.set(self.PLAYING_NOW_KEY + str(user_id), ujson.dumps(listen).encode('utf-8'), expirein=expire_time)

    def check_connection(self):
        """ Pings the redis server to check if the connection works or not """
        try:
            cache._r.ping()
        except redis.exceptions.ConnectionError as e:
            self.log.error("Redis ping didn't work: {}".format(str(e)))
            raise

    def update_recent_listens(self, unique):
        """
            Store the most recent listens in redis so we can fetch them easily for a recent listens page. This
            is not a critical action, so if it fails, it fails. Let's live with it.
        """

        recent = {}
        for listen in unique:
            recent[ujson.dumps(listen.to_json()).encode('utf-8')] = float(listen.ts_since_epoch)

        # Don't take this very seriously -- if it fails, really no big deal. Let is go.
        if recent:
            cache._r.zadd(cache._prep_key(self.RECENT_LISTENS_KEY), recent, nx=True)

            # Don't prune the sorted list each time, but only when it reaches twice the desired size
            count = cache._r.zcard(cache._prep_key(self.RECENT_LISTENS_KEY))
            if count > (self.RECENT_LISTENS_MAX * 2):
                cache._r.zpopmin(cache._prep_key(self.RECENT_LISTENS_KEY), count - self.RECENT_LISTENS_MAX - 1)

    def get_recent_listens(self, max = RECENT_LISTENS_MAX):
        """
            Get the max number of most recent listens
        """
        recent = []
        for listen in cache._r.zrevrange(cache._prep_key(self.RECENT_LISTENS_KEY), 0, max - 1):
            recent.append(Listen.from_json(ujson.loads(listen)))

        return recent

    def increment_listen_count_for_day(self, day: datetime, count: int):
        """ Increment the number of listens submitted on the day `day`
        by `count`.
        """
        key = self.LISTEN_COUNT_PER_DAY_KEY + day.strftime('%Y%m%d')
        cache.increment(key, amount=count)
        cache.expire(key, self.LISTEN_COUNT_PER_DAY_EXPIRY_TIME)

    def get_listen_count_for_day(self, day: datetime) -> Optional[int]:
        """ Get the number of listens submitted for day `day`, return None if not available.
        """
        key = self.LISTEN_COUNT_PER_DAY_KEY + day.strftime('%Y%m%d')
        listen_count = cache.get(key, decode=False)
        if listen_count:
            return int(listen_count)
        return None
