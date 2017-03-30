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
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import json

MIN_ID = 1033430400     # approx when audioscrobbler was created
ORDER_DESC = 0
ORDER_ASC = 1
ORDER_TEXT = [ "DESC", "ASC" ]
DEFAULT_LISTENS_PER_FETCH = 25

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

    def get_total_listen_count():
        """ Return the total number of listens stored in the ListenStore """
        raise NotImplementedError()

    def get_listen_count_for_user(self, user_name, need_exact):
        """ Override this method in ListenStore implementation class

        Args:
            user_name: the user to get listens for
            need_exact: if True, get an exact number of listens directly from the ListenStore
                        otherwise, can get from a cache also
        """
        raise NotImplementedError()

    def fetch_listens(self, user_name, from_ts=None, to_ts=None, limit=DEFAULT_LISTENS_PER_FETCH):
        """ Check from_ts, to_ts, and limit for fetching listens
            and set them to default values if not given.
        """
        if from_ts and to_ts:
            raise ValueError("You cannot specify from_ts and to_ts at the same time.")

        if not from_ts and not to_ts:
            raise ValueError("You must specify either from_ts or to_ts.")

        if from_ts:
            order = ORDER_ASC
        else:
            order = ORDER_DESC

        return self.fetch_listens_from_storage(user_name, from_ts, to_ts, limit, order)


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

    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
        """
        with self.engine.connect() as connection:
            args = {
                'user_name': user_name,
                'limit': limit
            }
            query = """
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
            """

            if from_ts != None:
                query += " AND ts AT TIME ZONE 'UTC' > :from_ts "
            else:
                query += " AND ts AT TIME ZONE 'UTC' < :to_ts "

            query += """
              ORDER BY ts """ + ORDER_TEXT[order] + """
                 LIMIT :limit
            """
            if from_ts != None:
                args['from_ts'] = pytz.utc.localize(datetime.utcfromtimestamp(from_ts))
            else:
                args['to_ts'] =  pytz.utc.localize(datetime.utcfromtimestamp(from_ts))

            results = connection.execute(text(query), args)
            listens = []
            for row in results.fetchall():
                listens.append(self.convert_row(row))
            return listens


class RedisListenStore(ListenStore):
    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.log.info('Connecting to redis: %s:%s', conf['REDIS_HOST'], conf['REDIS_PORT'])
        self.redis = Redis(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'])

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

    REDIS_INFLUX_TOTAL_LISTEN_COUNT = "ls.listencount.total"
    TOTAL_LISTEN_COUNT_CACHE_TIME = 10 * 60
    USER_LISTEN_COUNT_CACHE_TIME = 15 * 60 # in seconds. 15 minutes

    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.redis = Redis(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'])
        self.influx = InfluxDBClient(host=conf['INFLUX_HOST'], port=conf['INFLUX_PORT'], database=conf['INFLUX_DB_NAME'])


    def get_listen_count_for_user(self, user_name, need_exact=False):
        """Get the total number of listens for a user. The number of listens comes from
           a redis cache unless an exact number is asked for.

        Args:
            user_name: the user to get listens for
            need_exact: if True, get an exact number of listens directly from the ListenStore
        """

        if not need_exact:
            # check if the user's listen count is already in redis
            # if already present return it directly instead of calculating it again
            count = self.redis.get(REDIS_INFLUX_USER_LISTEN_COUNT + user_name)
            if count:
                return int(count)

        try:
            results = self.influx.query("""SELECT count(*)
                                             FROM listen
                                            WHERE user_name = '%s'""" % (user_name, ))
        except (InfluxDBServerError, InfluxDBClientError) as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        # get the number of listens from the json
        try:
            count = results.get_points(measurement = 'listen').next()['count_recording_msid']
        except (KeyError, StopIteration):
            count = 0

        # put this value into redis with an expiry time
        user_key = "{}{}".format(REDIS_INFLUX_USER_LISTEN_COUNT, user_name)
        self.redis.setex(user_key, count, InfluxListenStore.USER_LISTEN_COUNT_CACHE_TIME)
        return int(count)


    def reset_listen_count(self, user_name):
        """ Reset the listen count of a user from cache and put in a new calculated value.

            Args:
                user_name: the musicbrainz id of user whose listen count needs to be reset
        """
        get_listen_count_for_user(user_name, need_exact=True)


    def _select_single_value(self, query):
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        for result in results.get_points(measurement='listen'):
            return result['time']

        return None


    def _select_single_timestamp(self, query):
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        for result in results.get_points(measurement='listen'):
            dt = datetime.strptime(result['time'] , "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.strftime('%s'))

        return None

    def get_total_listen_count(self):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the redis cache for the value, if not present there
            makes a query to the db and caches it in redis.
        """

        count = self.redis.get(InfluxListenStore.REDIS_INFLUX_TOTAL_LISTEN_COUNT)
        if count:
            return int(count)

        try:
            result = self.influx.query("""SELECT count(*)
                                            FROM listen""")
        except (InfluxDBServerError, InfluxDBClientError) as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        try:
            count = result.get_points(measurement = 'listen').next()['count_recording_msid']
        except KeyError:
            count = 0

        self.redis.setex(InfluxListenStore.REDIS_INFLUX_TOTAL_LISTEN_COUNT, count, InfluxListenStore.TOTAL_LISTEN_COUNT_CACHE_TIME)
        return count


    def get_timestamps_for_user(self, user_name):
        """ Return the max_ts and min_ts for a given user and cache the result in redis
        """

        tss = self.redis.get(REDIS_USER_TIMESTAMPS % user_name)
        if tss:
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
        else:
            query = """SELECT first(artist_msid)
                         FROM listen
                        WHERE user_name = '""" + user_name + "'"
            min_ts = self._select_single_timestamp(query)

            query = """SELECT last(artist_msid)
                         FROM listen
                        WHERE user_name = '""" + user_name + "'"
            max_ts = self._select_single_timestamp(query)

            self.redis.setex(REDIS_USER_TIMESTAMPS % user_name, "%d,%d" % (min_ts,max_ts), USER_CACHE_TIME)

        return (min_ts, max_ts)


    def insert(self, listens):
        """ Insert a batch of listens.
        """

        submit = []
        user_names = {}
        for listen in listens:
            user_names[listen.user_name] = 1
            submit.append(listen.to_influx())


        try:
            if not self.influx.write_points(submit, time_precision='s'):
                self.log.error("Cannot write data to influx. (write_points returned False)")
        except (InfluxDBServerError, InfluxDBClientError, ValueError) as e:
            self.log.error("Cannot write data to influx: %s" % str(e))
            self.log.error("Data that was being written when the error occurred: ")
            self.log.error(json.dumps(submit, indent=4))
            raise

        # If we reach this point, we were able to write the listens to the InfluxListenStore.
        # So update the listen counts of the users cached in redis.
        for data in submit:
            user_key = "{}{}".format(REDIS_INFLUX_USER_LISTEN_COUNT, data['tags']['user_name'])
            if self.redis.exists(user_key):
                self.redis.incr(user_key)

        # Invalidate cached data for user
        for user_name in user_names.keys():
            self.redis.delete(REDIS_USER_TIMESTAMPS % user_name)

#        l = [ REDIS_INFLUX_USER_LISTEN_COUNT + str(id) for id in user_names])
#        self.log.info("delete: " % ",".join(l))
#        self.redis.delete(*[ REDIS_INFLUX_USER_LISTEN_COUNT + user_hash(user_name) for id in user_names])


    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order):
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
                    WHERE user_name = '""" + user_name + "' "
        if from_ts != None:
            query += "AND time > " + str(from_ts) + "000000000"
        else:
            query += "AND time < " + str(to_ts) + "000000000"

        query += " ORDER BY time " + ORDER_TEXT[order] + " LIMIT " + str(limit)
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            return []

        listens = []
        for result in results.get_points(measurement='listen'):
            listens.append(Listen.from_influx(result))

        if order == ORDER_ASC:
            listens.reverse()

        return listens
