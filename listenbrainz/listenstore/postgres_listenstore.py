# coding=utf-8


from listenbrainz.listenstore import ListenStore, ORDER_TEXT
import logging
import ujson
import time
import uuid
import pytz
from datetime import date, datetime
from listenbrainz.listen import Listen
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import sqlalchemy.exc
import json


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
                      release_msid=row[5], recording_msid=row[6], data=row[7])

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
                        'release_msid': uuid.UUID(listen.release_msid) if listen.release_msid is not None else None,
                        'recording_msid': uuid.UUID(listen.recording_msid),
                        'data': ujson.dumps(listen.data)}

                    res = connection.execute(text("""
                        INSERT INTO listen(user_id, ts, artist_msid, release_msid, recording_msid)
                             VALUES (:user_id, to_timestamp(:ts), :artist_msid, :release_msid,
                                    :recording_msid)
                                 ON CONFLICT(user_id, ts)
                                 DO UPDATE
                                SET artist_msid = EXCLUDED.artist_msid
                                  , release_msid = EXCLUDED.release_msid
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
                except Exception as e:     # Log errors
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
                     , release_msid
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

