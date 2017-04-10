# coding=utf-8
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals
from listenstore import ListenStore
import logging
from listen import Listen
from influxdb import InfluxDBClient
from redis import Redis
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import json
from listenstore import ORDER_DESC, ORDER_ASC, ORDER_TEXT, \
    USER_CACHE_TIME, REDIS_USER_TIMESTAMPS


REDIS_INFLUX_USER_LISTEN_COUNT = "ls.listencount." # append username

class InfluxListenStore(ListenStore):

    REDIS_INFLUX_TOTAL_LISTEN_COUNT = "ls.listencount.total"
    TOTAL_LISTEN_COUNT_CACHE_TIME = 10 * 60
    USER_LISTEN_COUNT_CACHE_TIME = 15 * 60 # in seconds. 15 minutes

    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.redis = Redis(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'])
        self.influx = InfluxDBClient(host=conf['INFLUX_HOST'], port=conf['INFLUX_PORT'], database=conf['INFLUX_DB_NAME'])

    @staticmethod
    def escape(value):
        return "\"{0}\"".format( value.replace("\\", "\\\\").replace( "\"", "\\\"").replace( "\n", "\\n"))

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
            results = self.influx.query('SELECT count(*) FROM "\\"' + user_name + '\\""')
        except (InfluxDBServerError, InfluxDBClientError) as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        # get the number of listens from the json
        try:
            count = results.get_points(measurement = self.escape(user_name)).next()['count_recording_msid']
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
        self.get_listen_count_for_user(user_name, need_exact=True)


    def _select_single_value(self, query, measurement):
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        for result in results.get_points(measurement=measurement):
            return result['time']

        return None


    def _select_single_timestamp(self, query, measurement):
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        for result in results.get_points(measurement=self.escape(measurement)):
            dt = datetime.strptime(result['time'] , "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.strftime('%s'))

        return None

    def get_total_listen_count(self):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the redis cache for the value, if not present there
            makes a query to the db and caches it in redis.
        """

        # In order to make this work again, we need to enumerate all the users and sum each one up. :(
        # TODO: Fix this and implement as a batch process that runs once a day
        return 0

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
            query = 'SELECT first(artist_msid) FROM "\\"' + user_name + '\\""'
            min_ts = self._select_single_timestamp(query, user_name)

            query = 'SELECT last(artist_msid) FROM "\\"' + user_name + '\\""'
            max_ts = self._select_single_timestamp(query, user_name)

            self.redis.setex(REDIS_USER_TIMESTAMPS % user_name, "%d,%d" % (min_ts,max_ts), USER_CACHE_TIME)

        return (min_ts, max_ts)


    def insert(self, listens):
        """ Insert a batch of listens.
        """

        submit = []
        user_names = {}
        for listen in listens:
            user_names[listen.user_name] = 1
            submit.append(listen.to_influx(self.escape(listen.user_name)))


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

        query = 'SELECT * FROM "\\"' + user_name + '\\""'

        # Quote single quote characters which could be used to mount an injection attack.
        # Sadly, influxdb does not provide a means to do this in the client library
        user_name = self.escape(user_name)

        if from_ts != None:
            query += "WHERE time > " + str(from_ts) + "000000000"
        else:
            query += "WHERE time < " + str(to_ts) + "000000000"

        query += " ORDER BY time " + ORDER_TEXT[order] + " LIMIT " + str(limit)
        try:
            results = self.influx.query(query)
        except Exception as e:
            self.log.error("Cannot query influx: %s" % str(e))
            return []

        listens = []
        for result in results.get_points(measurement=user_name):
            listens.append(Listen.from_influx(result))

        if order == ORDER_ASC:
            listens.reverse()

        return listens
