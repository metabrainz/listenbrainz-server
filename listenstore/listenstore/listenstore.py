# coding=utf-8
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals
import logging
import calendar
import json
import time
import uuid
from datetime import date, datetime
from .listen import Listen
from dateutil.relativedelta import relativedelta

from cassandra.cluster import Cluster
from cassandra import InvalidRequest
from cassandra.query import SimpleStatement, BatchStatement

MIN_ID = 1033430400     # approx when audioscrobbler was created


def id_to_date(id):
    return date.fromtimestamp(id)


def date_to_id(dateobj):
    return calendar.timegm(dateobj.timetuple())


def datetuple_to_id(datetuple):
    datetuple += (1,) * (3 - len(datetuple))
    return date_to_id(date(*datetuple))


def daterange(dat, precision):
    if precision == 'day':
        return (dat.year, dat.month, dat.day)
    elif precision == 'month':
        return (dat.year, dat.month)
    elif precision == 'year':
        return (dat.year,)


def next_daterange(dat, precision):
    if precision == 'year':
        return (dat[0] + 1, 1, 1)
    elif precision == 'month':
        if dat[1] == 12:
            return (dat[0] + 1, 1, 1)
        else:
            return (dat[0], dat[1] + 1, 1)
    elif precision == 'day':
        d = date(*dat) + relativedelta(days=1)
        return (d.year, d.month, d.day)


def dateranges(min_id, max_id, precision):
    min_date, max_date = id_to_date(min_id), id_to_date(max_id)
    if precision == 'day':
        delta = relativedelta(days=1)
    elif precision == 'month':
        delta = relativedelta(months=1)
    elif precision == 'year':
        delta = relativedelta(years=1)

    current = max_date

    while current >= min_date:
        yield daterange(current, precision)
        current -= delta


def range_keys(precision):
    res = "year = %(year)s"
    if precision >= 2:
        res += " AND month = %(month)s"
    if precision >= 3:
        res += " AND day = %(day)s"
    return res


def range_params(date_range):
    precision = len(date_range)
    params = {'year': date_range[0]}
    if precision >= 2:
        params['month'] = date_range[1]
    if precision >= 3:
        params['day'] = date_range[2]
    return params


class ListenStore(object):
    MAX_FETCH = 5000          # max batch size to fetch from cassandra
    MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew

    def __init__(self, conf):
        self.log = logging.getLogger(__name__)
        self.replication_factor = conf.get("replication_factor", 1)
        self.keyspace = conf.get("cassandra_keyspace", "listenbrainz")
        host = conf.get("cassandra_server", "localhost:9092")
        self.log.info('Connecting to cassandra: %s', host)
        self.cluster = Cluster([host])

        try:
            self.session = self.cluster.connect(self.keyspace)
        except InvalidRequest:
            self.log.info('Creating schema in keyspace %s...', self.keyspace)
            self.session = self.cluster.connect()
            self.create_schema()

    def execute(self, query, params=None):
        return self.session.execute(query.encode(), params)

    def create_schema(self):
        opts = {'repfactor': self.replication_factor, 'keyspace': self.keyspace}
        for query in CREATE_SCHEMA_QUERIES:
            self.execute(query % opts)

    def drop_schema(self):
        if self.keyspace == 'listenbrainz':
            raise Exception("Attempt to drop the production keyspace, denied.")
        self.log.info("Dropping keyspace %s...", self.keyspace)
        self.execute('DROP KEYSPACE %s' % self.keyspace)

    def max_id(self):
        return int(self.MAX_FUTURE_SECONDS + calendar.timegm(time.gmtime()))

    def insert_async(self, listen):
        batch = BatchStatement()
        query = """INSERT INTO listens
                    (uid, year, month, day, id, artist_msid, album_msid, track_msid, json)
                    VALUES (%(uid)s, %(year)s, %(month)s, %(day)s, %(id)s, %(artist_msid)s,
                            %(album_msid)s, %(track_msid)s, %(json)s)"""
        date = listen.date
        values = {'uid': listen.uid,
                  'year': date.year,
                  'month': date.month,
                  'day': date.day,
                  'id': int((listen.timestamp - datetime(1970, 1, 1)).total_seconds()),
                  'artist_msid': uuid.UUID(listen.artist_msid),
                  'album_msid': uuid.UUID(listen.album_msid) if listen.album_msid is not None else None,
                  'track_msid': uuid.UUID(listen.track_msid),
                  'json': json.dumps(listen.data)}
        batch.add(SimpleStatement(query), values)
        return self.session.execute_async(batch)

    def insert(self, listen):
#        if not listen.validate():
#            raise ValueError("Invalid listen: %s" % listen)
        self.insert_async(listen).result()

    def insert_batch(self, listens):
        """ Insert a batch of listens, using asynchronous queries.
            Batches should probably be no more than 500-1000 listens until this
            function supports limiting the number of queries in flight.
        """
        queries = []
        for listen in listens:
            queries.append(self.insert_async(listen))
        [query.result() for query in queries]

    def fetch_listens(self, uid, from_id=None, to_id=None, limit=None, order='desc'):
        """ Fetch a range of listens, for a user
        """
        precision = 'month'
        if from_id is None:
            from_id = MIN_ID
        if to_id is None:
            to_id = self.max_id()

        ranges = dateranges(from_id, to_id, precision)
        if order == 'asc':
            ranges = reversed(ranges)

        fetched_rows = 0
        for daterange in ranges:
            current_from_id = max(datetuple_to_id(daterange) - 1, from_id)
            current_to_id = min(datetuple_to_id(next_daterange(daterange, precision)), to_id)
            if limit is not None:
                current_limit = limit - fetched_rows
            else:
                current_limit = None

            for listen in self.fetch_listens_for_range(uid, daterange, current_from_id, current_to_id,
                                                       current_limit, order):
                yield listen
                fetched_rows += 1
                if limit is not None and fetched_rows == limit:
                    return

    def convert_row(self, row):
        return Listen(uid=row.uid, timestamp=datetime.fromtimestamp(row.id), album_msid=row.album_msid,
                      artist_msid=row.artist_msid, track_msid=row.track_msid, data=json.loads(row.json))

    def fetch_listens_for_range(self, uid, date_range, from_id, to_id, limit=None, order='desc'):
        """ Fetch listens for a specified uid within a single date range.

            date_range can be a 1-, 2-, or 3-tuple (year, month, day).

            This method will limit the amount of rows it fetches with one query,
            issuing multiple queries if the number of rows exceeds self.MAX_FETCH.
        """
        query = """SELECT * FROM listens WHERE uid = %(uid)s AND """ + \
                range_keys(len(date_range)) + \
                """ AND id >= %(from_id)s AND id <= %(to_id)s
                   ORDER BY id """ + order.upper() + """ LIMIT %(limit)s"""

        fetched_rows = 0  # Total number of rows fetched for this range

        while True:
            if limit is not None:
                # Only ask for the number of rows we need
                this_limit = min(limit - fetched_rows, self.MAX_FETCH)
            else:
                this_limit = self.MAX_FETCH

            params = {'uid': uid,
                      'from_id': from_id, 'to_id': to_id,
                      'limit': this_limit}

            params.update(range_params(date_range))

            this_batch = 0  # Number of rows we fetched in this batch

            self.log.debug("Fetching up to %s rows for date_range: %s, uid: %s", this_limit, date_range, uid)
            results = self.execute(query, params)
            for row in results:
                yield self.convert_row(row)
                fetched_rows += 1
                this_batch += 1
                if limit and fetched_rows == limit:
                    return

            if this_batch == self.MAX_FETCH:
                # We hit the maximum number of rows, so we need to fetch another batch. Move the id range:
                if order == 'asc':
                    from_id = row[0] + 1
                else:
                    to_id = row[0] - 1
            else:
                return


CREATE_SCHEMA_QUERIES = [
    """CREATE KEYSPACE %(keyspace)s WITH replication = {
        'class': 'SimpleStrategy',
        'replication_factor': '%(repfactor)s'
        }""",
    "USE %(keyspace)s",
    """CREATE TABLE listens (
        uid TEXT,
        year INT,
        month INT,
        day INT,
        id INT,
        artist_msid UUID,
        album_msid UUID,
        track_msid UUID,
        json TEXT,
        PRIMARY KEY ((uid, year, month), id)
    ) WITH CLUSTERING ORDER BY (id DESC) AND
        compaction={'sstable_size_in_mb': '256', 'class': 'LeveledCompactionStrategy'};
    """
]
