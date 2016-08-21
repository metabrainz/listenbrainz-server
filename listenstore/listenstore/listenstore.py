# coding=utf-8
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals
import logging
import calendar
import ujson
import time
import uuid
import six
from datetime import date, datetime
from listen import Listen
from dateutil.relativedelta import relativedelta

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc
import pytz
from redis import Redis

MIN_ID = 1033430400     # approx when audioscrobbler was created
ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]


class ListenStore(object):
    MAX_FETCH = 5000          # max batch size to fetch from the db
    MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew

    def __init__(self, conf):
        self.log = logging.getLogger(__name__)

    def max_id(self):
        return int(self.MAX_FUTURE_SECONDS + calendar.timegm(time.gmtime()))

    def fetch_listens_from_storage():
        """ Override this method in PostgresListenStore class """
        raise NotImplementedError()

    def fetch_listens(self, user_id, from_ts=None, to_ts=None, limit=None):
        """ Check from_ts, to_ts, and limit for fetching listens
            and set them to default values if not given.
        """
        if from_ts and to_ts:
            raise ValueError("You cannot specify from_ts and to_ts at the same time.")

        if from_ts:
            order = ORDER_ASC
        else:
            order = ORDER_DESC

        precision = 'month'
        if from_ts is None:
            from_ts = MIN_ID
        if to_ts is None:
            to_ts = self.max_id()
        return self.fetch_listens_from_storage(user_id, from_ts, to_ts, limit, order, precision)


class PostgresListenStore(ListenStore):
    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.log.info('Connecting to postgresql: %s', conf['SQLALCHEMY_DATABASE_URI'])
        self.engine = create_engine(conf['SQLALCHEMY_DATABASE_URI'], poolclass=NullPool)
        if 'PG_ASYNC_LISTEN_COMMIT' in conf and conf['PG_ASYNC_LISTEN_COMMIT']:
            self.log.info('Enabling Asynchronous listens commit for Postgresql')
            with self.engine.connect() as connection:
                connection.execute("SET synchronous_commit TO off")

    def convert_row(self, row):
        return Listen(user_id=row[1], timestamp=row[2], artist_msid=row[3], album_msid=row[4],
                      recording_msid=row[5], data=row[6])

    def insert(self, listens):
        """ Insert a batch of listens, using asynchronous queries.
            Batches should probably be no more than 500-1000 listens until this
            function supports limiting the number of queries in flight.
        """
        with self.engine.connect() as connection:
            for listen in listens:
                if not listen.validate():
                    raise ValueError("Invalid listen: %s" % listen)
                try:
                    params = {
                        'user_id': listen.user_id,
                        'ts': listen.timestamp,
                        'artist_msid': uuid.UUID(listen.artist_msid),
                        'album_msid': uuid.UUID(listen.album_msid) if listen.album_msid is not None else None,
                        'recording_msid': uuid.UUID(listen.recording_msid),
                        'data': ujson.dumps(listen.data)}

                    res = connection.execute(text("""
                        INSERT INTO listen(user_id, ts, artist_msid, album_msid, recording_msid)
                             VALUES (:user_id, to_timestamp(:ts), :artist_msid, :album_msid,
                                    :recording_msid)
                                 ON CONFLICT(user_id, ts)
                                 DO UPDATE
                                SET artist_msid = EXCLUDED.artist_msid
                                  , album_msid = EXCLUDED.album_msid
                                  , recording_msid = EXCLUDED.recording_msid
                          RETURNING id
                    """), params)

                    params['_id'] = res.fetchone()[0]
                    res = connection.execute(text("""
                        INSERT INTO listen_json(id, data)
                             VALUES (:_id, :data)
                                 ON CONFLICT(id)
                                 DO UPDATE
                                SET data = EXCLUDED.data
                    """), params)
                except Exception, e:     # Log errors
                    self.log.error(e)

    def fetch_listens_from_storage(self, user_id, from_ts, to_ts, limit, order, precision):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
        """
        with self.engine.connect() as connection:
            results = connection.execute(text("""
                SELECT listen.id
                     , user_id
                     , extract(epoch from ts)
                     , artist_msid
                     , album_msid
                     , recording_msid
                     , data
                  FROM listen
                     , listen_json
                 WHERE listen.id = listen_json.id
                   AND user_id = :user_id
                   AND ts AT TIME ZONE 'UTC' > :from_ts
                   AND ts AT TIME ZONE 'UTC' < :to_ts
              ORDER BY ts """ + ORDER_TEXT[order] + """
                 LIMIT :limit
            """), {
                'user_id': user_id,
                'from_ts': pytz.utc.localize(datetime.utcfromtimestamp(from_ts)),
                'to_ts': pytz.utc.localize(datetime.utcfromtimestamp(to_ts)),
                'limit': limit
            })

            listens = []
            for row in results.fetchall():
                listens.append(self.convert_row(row))
            return listens


class RedisListenStore(ListenStore):
    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.log.info('Connecting to redis: %s', conf['REDIS_HOST'])
        self.redis = Redis(conf['REDIS_HOST'])

    def get_playing_now(self, user_id):
        """ Return the current playing song of the user """
        data = self.redis.get('playing_now' + ':' + str(user_id))
        if not data:
            return None
        data = ujson.loads(data)
        data.update({'listened_at': datetime.utcnow()})
        return Listen.from_json(data)
