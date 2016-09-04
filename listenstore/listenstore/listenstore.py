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
from influxdb import InfluxDBClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc
import pytz
from redis import Redis

MIN_ID = 1033430400     # approx when audioscrobbler was created
ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]

REDIS_USER_TIMESTAMPS = "user.%s.timestamps" # substitute user_name
USER_CACHE_TIME = 3600 # in seconds. 1 hour

# TODO: This needs to be broken into 3 files and moved out of the separate listenstore module,
#       but I am leaving this for the next PR


class ListenStore(object):
    MAX_FETCH = 5000          # max batch size to fetch from the db
    MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew

    def __init__(self, conf):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.INFO)

    def max_id(self):
        return int(self.MAX_FUTURE_SECONDS + calendar.timegm(time.gmtime()))

    def fetch_listens_from_storage():
        """ Override this method in PostgresListenStore class """
        raise NotImplementedError()

    def fetch_listens(self, user_name, from_ts=None, to_ts=None, limit=None):
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
        return self.fetch_listens_from_storage(user_name, from_ts, to_ts, limit, order, precision)


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
        return Listen(user_id=row[1], user_name=row[2], timestamp=row[3], artist_msid=row[4], 
                      album_msid=row[5], recording_msid=row[6], data=row[7])

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
                        'ts': listen.ts_since_epoch,
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

    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order, precision):
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
                     , musicbrainz_id
                     , ts AT TIME ZONE 'UTC'
                     , artist_msid
                     , album_msid
                     , recording_msid
                     , data
                  FROM listen
                     , listen_json
                     , "user"
                 WHERE listen.id = listen_json.id
                   AND user_id = "user".id
                   AND "user".musicbrainz_id = :user_name
                   AND ts AT TIME ZONE 'UTC' > :from_ts
                   AND ts AT TIME ZONE 'UTC' < :to_ts
              ORDER BY ts """ + ORDER_TEXT[order] + """
                 LIMIT :limit
            """), {
                'user_name': user_name,
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
        data.update({'listened_at': MIN_ID+1})
        return Listen.from_json(data)



REDIS_INFLUX_USER_LISTEN_COUNT = "ls.listencount." # append username
class InfluxListenStore(ListenStore):
    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.redis = Redis(conf['REDIS_HOST'])
        self.influx = InfluxDBClient(host=conf['INFLUX_HOST'], port=conf['INFLUX_PORT'], database=conf['INFLUX_DB'])


    def _get_num_listens_for_user(self, user_name):
        count = self.redis.get(REDIS_INFLUX_USER_LISTEN_COUNT + user_hash(user_name))
        if count:
            return int(count)

        results = self.influx.query("""SELECT count(*) 
                                         FROM listen 
                                        WHERE user_name = '%s'""" % (user_name, from_ts, to_ts, limit))
        result = results.get_points(measurement='listen')
#        count = self.redis.get(REDIS_INFLUX_USER_LISTEN_COUNT + user_hash(user_name))

        return 0


    def _select_single_value(self, query):
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        for result in results.get_points(measurement='listen'):
            self.log.info(result['time'])
            return int(result['time'])

        return None


    def get_timestamps_for_user(self, user_name):
        """ Return the max_ts and min_ts for a given user and cache the result in redis
        """

        tss = self.redis.get(REDIS_USER_TIMESTAMPS % user_name)
        if tss:
            self.log.info("got tss from redis: ", tss)
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
        else:
            query = """SELECT first(track_name) 
                         FROM listen
                        WHERE user_name = '""" + user_name + "'"
            min_ts = self._select_single_value(query)

            query = """SELECT last(track_name)
                         FROM listen
                        WHERE user_name = '""" + user_name + "'"
            max_ts = self._select_single_value(query)

            self.log.info("set tss to redis: ", min_ts,max_ts)
            self.redis.setex(REDIS_USER_TIMESTAMPS % user_name, "%d,%d" % (min_ts,max_ts), USER_CACHE_TIME)

        return (min_ts, max_ts)


    def insert(self, listens):
        """ Insert a batch of listens.
        """

        submit = []
        user_names = {}
        for listen in listens:
            user_names[listen.user_name] = 1
            data = {
                'measurement' : 'listen',
                'time' : listen.ts_since_epoch,
                'tags' : {
                    'user_name' : listen.user_name,
                },
                'fields' : {
                    'artist_name' : listen.data['artist_name'],
                    'artist_msid' : listen.artist_msid,
                    'artist_mbids' : ",".join(listen.data['additional_info'].get('artist_mbids', [])),
                    'album_name' : listen.data['additional_info'].get('release_name', ''),
                    'album_msid' : listen.album_msid,
                    'album_mbid' : listen.data['additional_info'].get('release_mbid', ''),
                    'track_name' : listen.data['track_name'],
                    'recording_msid' : listen.recording_msid,
                    'recording_mbid' : listen.data['additional_info'].get('recording_mbid', ''),
                    'tags' : ",".join(listen.data['additional_info'].get('tags', [])),
                }
            }
            submit.append(data)


        try:
            if not self.influx.write_points(submit, time_precision='s'):
                self.log.error("Cannot write data to influx. (write_points returned False)")
        except ValueError as e:
            self.log.error("Cannot write data to influx: %s" % str(e))
            raise

        # Invalidate cached data for user
        self.r.delete(REDIS_USER_TIMESTAMPS)

#        l = [ REDIS_INFLUX_USER_LISTEN_COUNT + str(id) for id in user_names])
#        self.log.info("delete: " % ",".join(l))
#        self.redis.delete(*[ REDIS_INFLUX_USER_LISTEN_COUNT + user_hash(user_name) for id in user_names])


    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order, precision):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
        """

        # Quote single quote characters which could be used to mount an injection attack.
        # Sadly, influxdb does not provide a means to do this in the client library
        user_name = user_name.replace("'", "\'")

        query = """SELECT *
                     FROM listen
                    WHERE user_name = '""" + user_name + """'
                      AND time >= """ + str(from_ts) + """000000000
                      AND time <= """ + str(to_ts) + """000000000
                 ORDER BY time """ + ORDER_TEXT[order] 

        if limit:
            query += " LIMIT " + str(limit)

        self.log.info(query)
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            return []

        listens = []
        for result in results.get_points(measurement='listen'):
            dt = datetime.strptime(result['time'] , "%Y-%m-%dT%H:%M:%SZ")
            t = int(dt.strftime('%s'))
            mbids = []
            for id in result.get('artist_mbids', '').split(","):
                if id:
                    mbids.append(id) 
            tags = []
            for tag in result.get('tags', '').split(","):
                if tag:
                    tags.append(tag)

            data = {
                'artist_mbids' : mbids,
                'album_msid' : result.get('album_msid', ''),
                'album_mbid' : result.get('album_mbid', ''),
                'album_name' : result.get('album_name', ''),
                'recording_mbid' : result.get('recording_mbid', ''),
                'tags' : tags
            }
            l = Listen(timestamp=t,
                user_name=result['user_name'],
                artist_msid=result['artist_msid'],
                recording_msid=result['recording_msid'],
                data={ 
                    'additional_info' : data,
                    'artist_name' : result['artist_name'],
                    'track_name' : result['track_name']
                })
            listens.append(l)


        return listens
