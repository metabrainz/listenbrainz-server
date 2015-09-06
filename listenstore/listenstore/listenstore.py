# coding=utf-8
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals
import logging
import calendar
import json
import time

from cassandra.cluster import Cluster
from cassandra import InvalidRequest
from cassandra.query import SimpleStatement, BatchStatement

MIN_ID = 1033430400     # approx when audioscrobbler was created


def id_to_key(id):
    return id // 10000000


def key_to_id(key):
    return key * 10000000


class ListenStore(object):
    MAX_FETCH = 5000          # max batch size to fetch from cassandra
    MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew

    def __init__(self, conf):
        host = conf["cassandra_server"]
        self.log = logging.getLogger(__name__)
        # TODO: configured via config file, different in dev/prod
        self.replication_factor = 1
        self.keyspace = conf["cassandra_keyspace"]
        self.log.info('Connecting to cassandra: %s', host)
        self.cluster = Cluster([host])

        try:
            self.session = self.cluster.connect(self.keyspace)
        except InvalidRequest:
            self.log.info('Creating schema in keyspace %s...', self.keyspace)
            self.session = self.cluster.connect()
            self.create_schema()

        # Disable server-side paging because of CASSANDRA-8767
        self.session.default_fetch_size = None

    def execute(self, query, params=None):
        return self.session.execute(query.encode(), params)

    def create_schema(self):
        opts = {'repfactor': self.replication_factor, 'keyspace': self.keyspace}
        for query in CREATE_SCHEMA_QUERIES:
            self.execute(query % opts)

    def max_id(self):
        return int(self.MAX_FUTURE_SECONDS + calendar.timegm(time.gmtime()))

    def insert_async(self, item):
        batch = BatchStatement()
        tid = item['listened_at']
        idkey = id_to_key(tid)
        query = """INSERT INTO listens
                    (uid, idkey, id, json)
                    VALUES (%(uid)s, %(idkey)s, %(id)s, %(json)s)"""
        values = {'uid': item['user_id'],
                  'id': tid,
                  'idkey': idkey,
                  'json': json.dumps(item)}
        batch.add(SimpleStatement(query), values)
        return self.session.execute_async(batch)

    def insert(self, item):
        if "user_id" not in item:
            raise ValueError("user_id field missing")
        if "listened_at" not in item:
            raise ValueError("listened_at field missing")

        self.insert_async(item).result()

    def insert_batch(self, items):
        """ Insert a batch of items, using asynchronous queries.
            Batches should probably be no more than 500-1000 items until this
            function supports limiting the number of queries in flight.
        """
        queries = []
        for item in items:
            queries.append(self.insert_async(item))
        [query.result() for query in queries]

    def keyrange(self, minid, maxid):
        minv = id_to_key(minid)
        maxv = id_to_key(maxid)
        r = range(maxv, minv - 1, -1)
        return r

    def fetch_listens(self, uid, from_id=None, to_id=None, limit=None, order='desc'):
        """ Fetch a range of listens, for a user
        """
        if from_id is None:
            from_id = MIN_ID
        if to_id is None:
            to_id = self.max_id()

        idkeyrange = self.keyrange(from_id, to_id)
        if order == 'asc':
            idkeyrange = reversed(idkeyrange)

        fetched_rows = 0
        for idkey in idkeyrange:
            current_from_id = max(key_to_id(idkey) - 1, from_id)
            current_to_id = min(key_to_id(idkey + 1), to_id)
            if limit is not None:
                current_limit = limit - fetched_rows
            else:
                current_limit = None

            for listen in self.fetch_listens_for_idkey(uid, idkey, current_from_id, current_to_id,
                                                     current_limit, order):
                yield listen
                fetched_rows += 1
                if limit is not None and fetched_rows == limit:
                    return

    def fetch_listens_for_idkey(self, uid, idkey, from_id, to_id, limit=None, order='desc'):
        """ Fetch listens for a specified uid within a single idkey.

            This method will limit the amount of rows it fetches with one query,
            issuing multiple queries if the number of rows exceeds self.MAX_FETCH.
        """
        query = """SELECT id, json FROM listens WHERE uid = %(uid)s AND
                   idkey = %(idkey)s AND id >= %(from_id)s AND id <= %(to_id)s
                   ORDER BY id """ + order.upper() + """ LIMIT %(limit)s"""

        fetched_rows = 0  # Total number of rows fetched for this idkey

        while True:
            if limit is not None:
                # Only ask for the number of rows we need
                this_limit = min(limit - fetched_rows, self.MAX_FETCH)
            else:
                this_limit = self.MAX_FETCH

            params = {'uid': uid, 'idkey': idkey,
                      'from_id': from_id, 'to_id': to_id,
                      'limit': this_limit}

            this_batch = 0  # Number of rows we fetched in this batch

            self.log.debug("Fetching up to %s rows for idkey: %s, uid: %s", this_limit, idkey, uid)
            results = self.execute(query, params)
            for row in results:
                yield row
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

    def get_last_n(self, uid, limit=10, minid=None, maxid=None):
        if minid is None:
            minid = MIN_ID
        if maxid is None:
            maxid = self.max_id()
        # Not an error, some can have no listens, just early return
        if minid == 0 or maxid == 0:
            return
        else:
            return self.fetch_listens(uid, minid, maxid, limit)

    def get_since(self, uid, sinceid, maxid=None, limit=10):
        if sinceid < MIN_ID:
            # This should never happen, and it's inefficient when it does.
            sinceid = MIN_ID

        if maxid is None:
            maxid = self.max_id()

        if sinceid > maxid:
            return []
        else:
            return self.fetch_listens(uid, from_id=sinceid, to_id=maxid, limit=limit)

    def get_previous_n(self, uid, id, limit):  # TODO need minid from buffers table
        return self.fetch_listens(uid, None, id, limit)


CREATE_SCHEMA_QUERIES = [
    """CREATE KEYSPACE %(keyspace)s WITH replication = {
        'class': 'SimpleStrategy',
        'replication_factor': '%(repfactor)s'
        }""",
    "USE %(keyspace)s",
    """CREATE TABLE listens (
        uid text,
        idkey int,
        id int,
        json text,
        PRIMARY KEY ((uid, idkey), id)
    ) WITH CLUSTERING ORDER BY (id DESC) AND
        compaction={'sstable_size_in_mb': '256', 'class': 'LeveledCompactionStrategy'};
    """
]
