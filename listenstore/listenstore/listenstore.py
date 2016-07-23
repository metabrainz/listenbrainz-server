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
from .listen import Listen
from dateutil.relativedelta import relativedelta

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc

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


    def fetch_listens(self, user_id, from_id=None, to_id=None, limit=None):
        """ Check from_id, to_id, and limit for fetching listens
            and set them to default values if not given.
        """
        if from_id and to_id:
            raise ValueError("You cannot specify from_id and to_id at the same time.")

        if from_id:
            order = ORDER_ASC
        else:
            order = ORDER_DESC

        precision = 'month'
        if from_id is None:
            from_id = MIN_ID
        if to_id is None:
            to_id = self.max_id()
        return self.fetch_listens_from_storage(user_id, from_id, to_id, limit, order, precision)


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

    def format_dict(self, listen):
        return { 'user_id': listen.user_id,
                 'ts': listen.timestamp,
                 'artist_msid': uuid.UUID(listen.artist_msid),
                 'album_msid': uuid.UUID(listen.album_msid) if listen.album_msid is not None else None,
                 'recording_msid': uuid.UUID(listen.recording_msid),
                 'raw_data': ujson.dumps(listen.data)}

    def insert_postgresql(self, listens):
        """ Insert a batch of listens, using asynchronous queries.
            Batches should probably be no more than 500-1000 listens until this
            function supports limiting the number of queries in flight.
        """
        with self.engine.connect() as connection:
            for listen in listens:
                if not listen.validate():
                    raise ValueError("Invalid listen: %s" % listen)
                try:
                    res = connection.execute(
                    """ INSERT INTO listen(user_id, ts, artist_msid, album_msid, recording_msid, raw_data)
                        VALUES ( %(user_id)s, to_timestamp(%(ts)s), %(artist_msid)s, %(album_msid)s,
                        %(recording_msid)s, %(raw_data)s) ON CONFLICT DO NOTHING """, self.format_dict(listen))
                except Exception, e:     # Log errors
                        self.log.error(e)

    def execute(self, query, params={}):
        with self.engine.connect() as connection:
            res = connection.execute(query, params)
            return res.fetchall()

    def fetch_listens_from_storage(self, user_id, from_id, to_id, limit, order, precision):
        query = """ SELECT id, user_id, extract(epoch from ts), artist_msid, album_msid, recording_msid, raw_data """ + \
                """ FROM listen WHERE user_id = %(user_id)s """ + \
                """ AND extract(epoch from ts) > %(from_id)s AND extract(epoch from ts) < %(to_id)s  """ + \
                """ ORDER BY extract(epoch from ts) """ + ORDER_TEXT[order] + """ LIMIT %(limit)s"""
        params = {
            'user_id': user_id,
            'from_id': from_id,
            'to_id': to_id,
            'limit': limit
        }

        results = self.execute(query, params)
        for row in results:
            yield self.convert_row(row)
