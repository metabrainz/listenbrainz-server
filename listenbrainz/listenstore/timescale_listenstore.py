# coding=utf-8

import os
import subprocess
import tarfile
import tempfile
import time
import shutil
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
import ujson
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.errors import UntranslatableCharacter
from typing import List
import sqlalchemy

from brainzutils import cache

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale
from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listen import Listen
from listenbrainz.listenstore import ListenStore
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.utils import create_path, init_cache

# Append the user name for both of these keys
REDIS_USER_LISTEN_COUNT = "lc."
REDIS_USER_TIMESTAMPS = "ts."
REDIS_TOTAL_LISTEN_COUNT = "lc-total"

DUMP_CHUNK_SIZE = 100000
NUMBER_OF_USERS_PER_DIRECTORY = 1000
DUMP_FILE_SIZE_LIMIT = 1024 * 1024 * 1024  # 1 GB
DATA_START_YEAR = 2005
DATA_START_YEAR_IN_SECONDS = 1104537600

# How many listens to fetch on the first attempt. If we don't fetch enough, increase it by WINDOW_SIZE_MULTIPLIER
DEFAULT_FETCH_WINDOW = 30 * 86400  # 30 days

# When expanding the search, how fast should the bounds be moved out
WINDOW_SIZE_MULTIPLIER = 3

LISTEN_COUNT_BUCKET_WIDTH = 2592000


class TimescaleListenStore(ListenStore):
    '''
        The listenstore implementation for the timescale DB.
    '''

    def __init__(self, conf, logger):
        super(TimescaleListenStore, self).__init__(logger)

        timescale.init_db_connection(conf['SQLALCHEMY_TIMESCALE_URI'])

        # Initialize brainzutils cache
        init_cache(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'],
                   namespace=conf['REDIS_NAMESPACE'])
        self.dump_temp_dir_root = conf.get(
            'LISTEN_DUMP_TEMP_DIR_ROOT', tempfile.mkdtemp())

    def set_empty_cache_values_for_user(self, user_name):
        """When a user is created, set the listen_count and timestamp keys so that we
           can avoid the expensive lookup for a brand new user."""

        cache.set(REDIS_USER_LISTEN_COUNT + user_name, 0, time=0, encode=False)
        cache.set(REDIS_USER_TIMESTAMPS + user_name, "0,0", time=0)

    def get_listen_count_for_user(self, user_name):
        """Get the total number of listens for a user. The number of listens comes from
           brainzutils cache unless an exact number is asked for.

        Args:
            user_name: the user to get listens for
        """

        count = cache.get(REDIS_USER_LISTEN_COUNT + user_name, decode=False)
        if count is None:
            return self.reset_listen_count(user_name)
        else:
            return int(count)

    def reset_listen_count(self, user_name):
        """ Reset the listen count of a user from cache and put in a new calculated value.
            returns the re-calculated listen count.

            Args:
                user_name: the musicbrainz id of user whose listen count needs to be reset
        """
        query = "SELECT SUM(count) FROM listen_count_30day WHERE user_name = :user_name"
        t0 = time.monotonic()
        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query), {
                    "user_name": user_name,
                })
                count = int(result.fetchone()[0] or 0)

        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" %
                           str(e), exc_info=True)
            raise

        # intended for production monitoring
        self.log.info("listen counts %s %.2fs" % (user_name, time.monotonic() - t0))
        # put this value into brainzutils cache without an expiry time
        cache.set(REDIS_USER_LISTEN_COUNT + user_name,
                  count, time=0, encode=False)
        return count

    def update_timestamps_for_user(self, user_name, min_ts, max_ts):
        """
            If any code adds/removes listens it should update the timestamps for the user
            using this function, so that they values in redis are always current.

            If the given timestamps represent a new min or max value, these values will be
            saved in the cache, otherwise the user timestamps remain unchanged.
        """

        cached_min_ts, cached_max_ts = self.get_timestamps_for_user(user_name)
        if min_ts < cached_min_ts or max_ts > cached_max_ts:
            if min_ts < cached_min_ts:
                cached_min_ts = min_ts
            if max_ts > cached_max_ts:
                cached_max_ts = max_ts
            cache.set(REDIS_USER_TIMESTAMPS + user_name, "%d,%d" %
                      (cached_min_ts, cached_max_ts), time=0)

    def get_timestamps_for_user(self, user_name):
        """ Return the max_ts and min_ts for a given user and cache the result in brainzutils cache
        """

        tss = cache.get(REDIS_USER_TIMESTAMPS + user_name)
        if tss:
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
        else:
            t0 = time.monotonic()
            min_ts = self._select_single_timestamp(True, user_name)
            max_ts = self._select_single_timestamp(False, user_name)
            cache.set(REDIS_USER_TIMESTAMPS + user_name, "%d,%d" % (min_ts, max_ts), time=0)
            # intended for production monitoring
            self.log.info("timestamps %s %.2fs" % (user_name, time.monotonic() - t0))

        return min_ts, max_ts

    def _select_single_timestamp(self, select_min_timestamp, user_name):
        """ Fetch a single timestamp (min or max) from the listenstore for a given user.

            Args:
                select_min_timestamp: boolean. Select the min timestamp if true, max if false.
                user_name: the user for whom to fetch the timestamp.

            Returns:

                The selected timestamp for the user or 0 if no timestamp was found.
        """

        function = "max"
        if select_min_timestamp:
            function = "min"

        query = """SELECT %s(listened_at) AS ts
                     FROM listen
                     WHERE user_name = :user_name""" % function
        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query), {
                    "user_name": user_name
                })
                row = result.fetchone()
                if row is None or row['ts'] is None:
                    return 0

                return row['ts']

        except psycopg2.OperationalError as e:
            self.log.error("Cannot fetch min/max timestamp: %s" %
                           str(e), exc_info=True)
            raise

    def get_total_listen_count(self, cache_value=True):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the brainzutils cache for the value, if not present there
            makes a query to the db and caches it in brainzutils cache.
        """

        if cache_value:
            count = cache.get(REDIS_TOTAL_LISTEN_COUNT)
            if count:
                return int(count)

        query = "SELECT SUM(count) AS value FROM listen_count_30day"

        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query))
                count = int(result.fetchone()["value"] or "0")
        except psycopg2.OperationalError as e:
            self.log.error(
                "Cannot query timescale listen_count_30day: %s" % str(e), exc_info=True)
            raise

        if cache_value:
            cache.set(REDIS_TOTAL_LISTEN_COUNT, count, time=0)
        return count

    def insert(self, listens):
        """
            Insert a batch of listens. Returns a list of (listened_at, track_name, user_name) that indicates
            which rows were inserted into the DB. If the row is not listed in the return values, it was a duplicate.
        """

        submit = []
        for listen in listens:
            submit.append(listen.to_timescale())

        query = """INSERT INTO listen (listened_at, track_name, user_name, data)
                        VALUES %s
                   ON CONFLICT (listened_at, track_name, user_name)
                    DO NOTHING
                     RETURNING listened_at, track_name, user_name"""

        inserted_rows = []
        conn = timescale.engine.raw_connection()
        with conn.cursor() as curs:
            try:
                execute_values(curs, query, submit, template=None)
                while True:
                    result = curs.fetchone()
                    if not result:
                        break
                    inserted_rows.append((result[0], result[1], result[2]))
            except UntranslatableCharacter:
                conn.rollback()
                return

        conn.commit()

        # update the listen counts and timestamps for the users
        user_timestamps = {}
        user_counts = defaultdict(int)
        for ts, _, user_name in inserted_rows:
            if listen.user_name in user_timestamps:
                if ts < user_timestamps[listen.user_name][0]:
                    user_timestamps[listen.user_name][0] = ts
                if ts > user_timestamps[listen.user_name][1]:
                    user_timestamps[listen.user_name][1] = ts
            else:
                user_timestamps[listen.user_name] = [ts, ts]

            user_counts[user_name] += 1

        for user_name in user_counts:
            cache._r.incrby(cache._prep_key(
                REDIS_USER_LISTEN_COUNT + user_name), user_counts[user_name])

        for user in user_timestamps:
            self.update_timestamps_for_user(
                user, user_timestamps[user][0], user_timestamps[user][1])

        return inserted_rows

    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            If neither from_ts nor to_ts is provided, the latest listens for the user are returned.
            Returns a tuple of (listens, min_user_timestamp, max_user_timestamp)

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
            limit: the maximum number of items to return
            order: 0 for ASCending order, 1 for DESCending order
        """

        return self.fetch_listens_for_multiple_users_from_storage([user_name], from_ts, to_ts, limit, order)

    def fetch_listens_for_multiple_users_from_storage(self, user_names: List[str], from_ts: float, to_ts: float, limit: int, order: int):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            If neither from_ts nor to_ts is provided, the latest listens for the user are returned.
            Returns a tuple of (listens, min_user_timestamp, max_user_timestamp)

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
            limit: the maximum number of items to return
            order: 0 for DESCending order, 1 for ASCending order
        """

        min_user_ts = max_user_ts = None
        for user_name in user_names:
            min_ts, max_ts = self.get_timestamps_for_user(user_name)
            min_user_ts = min(min_ts, min_user_ts or min_ts)
            max_user_ts = max(max_ts, max_user_ts or max_ts)

        if to_ts is None and from_ts is None:
            to_ts = max_user_ts + 1

        if min_user_ts == 0 and max_user_ts == 0:
            return ([], min_user_ts, max_user_ts)

        window_size = DEFAULT_FETCH_WINDOW
        query = """SELECT listened_at, track_name, user_name, created, data
                     FROM listen
                    WHERE user_name IN :user_names
                      AND listened_at > :from_ts
                      AND listened_at < :to_ts
                 ORDER BY listened_at """ + ORDER_TEXT[order] + " LIMIT :limit"

        if from_ts and to_ts:
            to_dynamic = False
            from_dynamic = False
        elif from_ts is not None:
            to_ts = from_ts + window_size
            to_dynamic = True
            from_dynamic = False
        else:
            from_ts = to_ts - window_size
            to_dynamic = False
            from_dynamic = True

        listens = []
        done = False
        with timescale.engine.connect() as connection:
            t0 = time.monotonic()

            passes = 0
            while True:
                passes += 1

                # Oh shit valve. I'm keeping it here for the time being. :)
                if passes == 10:
                    done = True
                    break

                curs = connection.execute(sqlalchemy.text(query), user_names=tuple(user_names),
                                          from_ts=from_ts, to_ts=to_ts, limit=limit)
                while True:
                    result = curs.fetchone()
                    if not result:
                        if not to_dynamic and not from_dynamic:
                            done = True
                            break

                        if from_ts < min_user_ts - 1:
                            done = True
                            break

                        if to_ts > int(time.time()) + ListenStore.MAX_FUTURE_SECONDS:
                            done = True
                            break

                        if to_dynamic:
                            from_ts += window_size - 1
                            window_size *= WINDOW_SIZE_MULTIPLIER
                            to_ts += window_size

                        if from_dynamic:
                            to_ts -= window_size
                            window_size *= WINDOW_SIZE_MULTIPLIER
                            from_ts -= window_size

                        break

                    listens.append(Listen.from_timescale(*result))
                    if len(listens) == limit:
                        done = True
                        break

                if done:
                    break

            fetch_listens_time = time.monotonic() - t0

        if order == ORDER_ASC:
            listens.reverse()

        self.log.info("fetch listens %s %.2fs (%d passes)" %
                      (str(user_names), fetch_listens_time, passes))

        return (listens, min_user_ts, max_user_ts)

    def fetch_recent_listens_for_users(self, user_list, limit=2, max_age=3600):
        """ Fetch recent listens for a list of users, given a limit which applies per user. If you
            have a limit of 3 and 3 users you should get 9 listens if they are available.

            user_list: A list containing the users for which you'd like to retrieve recent listens.
            limit: the maximum number of listens for each user to fetch.
            max_age: Only return listens if they are no more than max_age seconds old. Default 3600 seconds
        """

        args = {'user_list': tuple(user_list), 'ts': int(
            time.time()) - max_age, 'limit': limit}
        query = """SELECT * FROM (
                              SELECT listened_at, track_name, user_name, created, data,
                                     row_number() OVER (partition by user_name ORDER BY listened_at DESC) AS rownum
                                FROM listen
                               WHERE user_name IN :user_list
                                 AND listened_at > :ts
                            GROUP BY user_name, listened_at, track_name, created, data
                            ORDER BY listened_at DESC) tmp
                           WHERE rownum <= :limit"""

        listens = []
        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query), args)
            while True:
                result = curs.fetchone()
                if not result:
                    break

                listens.append(Listen.from_timescale(
                    result[0], result[1], result[2], result[3], result[4]))

        return listens

    def get_listens_query_for_dump(self, start_time, end_time):
        """
            Get a query and its args dict to select a batch for listens for the full dump.
            Use listened_at timestamp, since not all listens have the created timestamp.
        """

        query = """SELECT listened_at, track_name, user_name, created, data
                     FROM listen
                    WHERE listened_at >= :start_time
                      AND listened_at <= :end_time
                 ORDER BY listened_at ASC"""
        args = {
            'start_time': start_time,
            'end_time': end_time
        }

        return (query, args)

    def get_incremental_listens_query(self, start_time, end_time):
        """
            Get a query for a batch of listens for an incremental listen dump.
            This uses the `created` column to fetch listens.
        """

        query = """SELECT listened_at, track_name, user_name, created, data
                     FROM listen
                    WHERE created > :start_ts
                      AND created <= :end_ts
                 ORDER BY created ASC"""

        args = {
            'start_ts': start_time,
            'end_ts': end_time,
        }
        return (query, args)

    def write_dump_metadata(self, archive_name, start_time, end_time, temp_dir, tar, full_dump=True):
        """ Write metadata files (schema version, timestamps, license) into the dump archive.

        Args:
            archive_name: the name of the archive
            start_time and end_time: the time range of the dump
            temp_dir: the directory to use for writing files before addition into the archive
            tar (TarFile object): The tar file to add the files into
            full_dump (bool): flag to specify whether the archive is a full dump or an incremental dump
        """
        try:
            if full_dump:
                # add timestamp
                timestamp_path = os.path.join(temp_dir, 'TIMESTAMP')
                with open(timestamp_path, 'w') as f:
                    f.write(end_time.isoformat(' '))
                tar.add(timestamp_path,
                        arcname=os.path.join(archive_name, 'TIMESTAMP'))
            else:
                start_timestamp_path = os.path.join(
                    temp_dir, 'START_TIMESTAMP')
                with open(start_timestamp_path, 'w') as f:
                    f.write(start_time.isoformat(' '))
                tar.add(start_timestamp_path,
                        arcname=os.path.join(archive_name, 'START_TIMESTAMP'))
                end_timestamp_path = os.path.join(temp_dir, 'END_TIMESTAMP')
                with open(end_timestamp_path, 'w') as f:
                    f.write(end_time.isoformat(' '))
                tar.add(end_timestamp_path,
                        arcname=os.path.join(archive_name, 'END_TIMESTAMP'))

            # add schema version
            schema_version_path = os.path.join(temp_dir, 'SCHEMA_SEQUENCE')
            with open(schema_version_path, 'w') as f:
                f.write(str(LISTENS_DUMP_SCHEMA_VERSION))
            tar.add(schema_version_path,
                    arcname=os.path.join(archive_name, 'SCHEMA_SEQUENCE'))

            # add copyright notice
            tar.add(DUMP_LICENSE_FILE_PATH,
                    arcname=os.path.join(archive_name, 'COPYING'))

        except IOError as e:
            self.log.critical(
                'IOError while writing metadata dump files: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            self.log.error(
                'Exception while adding dump metadata: %s', str(e), exc_info=True)
            raise

    def write_listens(self, temp_dir, tar_file, archive_name, start_time_range=None, end_time_range=None, full_dump=True):
        """ Dump listens in the format for the ListenBrainz dump.

        Args:
            end_time_range (datetime): the range of time for the listens dump.
            temp_dir (str): the dir to use to write files before adding to archive
            full_dump (bool): the type of dump
        """
        t0 = time.monotonic()
        listen_count = 0

        # This right here is why we should ONLY be using seconds timestamps. Someone could
        # pass in a timezone aware timestamp (when listens have no timezones) or one without.
        # If you pass the wrong one and a test invokes a command line any failures are
        # invisible causing massive hair-pulling. FUCK DATETIME.
        if start_time_range:
            start_time_range = datetime.utcfromtimestamp(
                datetime.timestamp(start_time_range))
        if end_time_range:
            end_time_range = datetime.utcfromtimestamp(
                datetime.timestamp(end_time_range))

        year = start_time_range.year
        month = start_time_range.month
        while True:
            start_time = datetime(year, month, 1)
            start_time = max(start_time_range, start_time)
            if start_time > end_time_range:
                break

            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year += 1

            end_time = datetime(next_year, next_month, 1)
            end_time = end_time - timedelta(seconds=1)
            if end_time > end_time_range:
                end_time = end_time_range

            filename = os.path.join(temp_dir, str(year), "%d.listens" % month)
            try:
                os.makedirs(os.path.join(temp_dir, str(year)))
            except FileExistsError:
                pass

            query, args = None, None
            if full_dump:
                query, args = self.get_listens_query_for_dump(int(start_time.strftime('%s')),
                                                              int(end_time.strftime('%s')))
            else:
                query, args = self.get_incremental_listens_query(
                    start_time, end_time)

            rows_added = 0
            with timescale.engine.connect() as connection:
                curs = connection.execute(sqlalchemy.text(query), args)
                if curs.rowcount:
                    with open(filename, "w") as out_file:
                        while True:
                            result = curs.fetchone()
                            if not result:
                                break

                            listen = Listen.from_timescale(
                                result[0], result[1], result[2], result[3], result[4]).to_json()
                            out_file.write(ujson.dumps(listen) + "\n")
                            rows_added += 1
                    tar_file.add(filename, arcname=os.path.join(
                        archive_name, 'listens', str(year), "%d.listens" % month))

                    listen_count += rows_added
                    self.log.info("%d listens dumped for %s at %.2f listens/s", listen_count, start_time.strftime("%Y-%m-%d"),
                                  listen_count / (time.monotonic() - t0))

            month = next_month
            year = next_year
            rows_added = 0

    def dump_listens(self, location, dump_id, start_time=datetime.utcfromtimestamp(0), end_time=None,
                     threads=DUMP_DEFAULT_THREAD_COUNT):
        """ Dumps all listens in the ListenStore into a .tar.xz archive.

        Files are created with UUIDs as names. Each file can contain listens for a number of users.
        An index.json file is used to save which file contains the listens of which users.

        This creates an incremental dump if start_time is specified (with range start_time to end_time),
        otherwise it creates a full dump with all listens.

        Args:
            location: the directory where the listens dump archive should be created
            dump_id (int): the ID of the dump in the dump sequence
            start_time and end_time (datetime): the time range for which listens should be dumped
                start_time defaults to utc 0 (meaning a full dump) and end_time defaults to the current time
            threads (int): the number of threads to use for compression
            spark_format (bool): dump files in Apache Spark friendly format if True, else full dumps

        Returns:
            the path to the dump archive
        """

        if end_time is None:
            end_time = datetime.now()

        self.log.info('Beginning dump of listens from TimescaleDB...')
        full_dump = bool(start_time == datetime.utcfromtimestamp(0))
        archive_name = 'listenbrainz-listens-dump-{dump_id}-{time}'.format(dump_id=dump_id,
                                                                           time=end_time.strftime('%Y%m%d-%H%M%S'))
        if full_dump:
            archive_name = '{}-full'.format(archive_name)
        else:
            archive_name = '{}-incremental'.format(archive_name)
        archive_path = os.path.join(
            location, '{filename}.tar.xz'.format(filename=archive_name))
        with open(archive_path, 'w') as archive:

            pxz_command = ['pxz', '--compress',
                           '-T{threads}'.format(threads=threads)]
            pxz = subprocess.Popen(
                pxz_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:

                temp_dir = os.path.join(
                    self.dump_temp_dir_root, str(uuid.uuid4()))
                create_path(temp_dir)
                self.write_dump_metadata(
                    archive_name, start_time, end_time, temp_dir, tar, full_dump)

                listens_path = os.path.join(temp_dir, 'listens')
                self.write_listens(listens_path, tar, archive_name,
                                   start_time, end_time, full_dump)

                # remove the temporary directory
                shutil.rmtree(temp_dir)

            pxz.stdin.close()

        pxz.wait()
        self.log.info('ListenBrainz listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path

    def import_listens_dump(self, archive_path, threads=DUMP_DEFAULT_THREAD_COUNT):
        """ Imports listens into TimescaleDB from a ListenBrainz listens dump .tar.xz archive.

        Args:
            archive (str): the path to the listens dump .tar.xz archive to be imported
            threads (int): the number of threads to be used for decompression
                           (defaults to DUMP_DEFAULT_THREAD_COUNT)

        Returns:
            int: the number of users for whom listens have been imported
        """

        self.log.info(
            'Beginning import of listens from dump %s...', archive_path)

        # construct the pxz command to decompress the archive
        pxz_command = ['pxz', '--decompress', '--stdout',
                       archive_path, '-T{threads}'.format(threads=threads)]
        pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

        schema_checked = False
        total_imported = 0
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            listens = []
            for member in tar:
                if member.name.endswith('SCHEMA_SEQUENCE'):
                    self.log.info(
                        'Checking if schema version of dump matches...')
                    schema_seq = int(tar.extractfile(
                        member).read().strip() or '-1')
                    if schema_seq != LISTENS_DUMP_SCHEMA_VERSION:
                        raise SchemaMismatchException('Incorrect schema version! Expected: %d, got: %d.'
                                                      'Please ensure that the data dump version matches the code version'
                                                      'in order to import the data.'
                                                      % (LISTENS_DUMP_SCHEMA_VERSION, schema_seq))
                    schema_checked = True

                if member.name.endswith(".listens"):
                    if not schema_checked:
                        raise SchemaMismatchException(
                            "SCHEMA_SEQUENCE file missing from listen dump.")

                    # tarf, really? That's the name you're going with? Yep.
                    with tar.extractfile(member) as tarf:
                        while True:
                            line = tarf.readline()
                            if not line:
                                break

                            listen = Listen.from_json(ujson.loads(line))
                            listens.append(listen)

                            if len(listens) > DUMP_CHUNK_SIZE:
                                total_imported += len(listens)
                                self.insert(listens)
                                listens = []

            if len(listens) > 0:
                total_imported += len(listens)
                self.insert(listens)

        if not schema_checked:
            raise SchemaMismatchException(
                "SCHEMA_SEQUENCE file missing from listen dump.")

        self.log.info('Import of listens from dump %s done!', archive_path)
        pxz.stdout.close()

        return total_imported

    def delete(self, musicbrainz_id):
        """ Delete all listens for user with specified MusicBrainz ID.

        Note: this method tries to delete the user 5 times before giving up.

        Args:
            musicbrainz_id (str): the MusicBrainz ID of the user

        Raises: Exception if unable to delete the user in 5 retries
        """

        self.set_empty_cache_values_for_user(musicbrainz_id)
        args = {'user_name': musicbrainz_id}
        query = "DELETE FROM listen WHERE user_name = :user_name"

        try:
            with timescale.engine.connect() as connection:
                connection.execute(sqlalchemy.text(query), args)
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listens for user: %s" % str(e))
            raise

    def delete_listen(self, listened_at: int, user_name: str, recording_msid: str):
        """ Delete a particular listen for user with specified MusicBrainz ID.
        Args:
            listened_at: The timestamp of the listen
            user_name: the username of the user
            recording_msid: the MessyBrainz ID of the recording
        Raises: TimescaleListenStoreException if unable to delete the listen
        """

        args = {'listened_at': listened_at, 'user_name': user_name,
                'recording_msid': recording_msid}
        query = """DELETE FROM listen
                    WHERE listened_at = :listened_at
                      AND user_name = :user_name
                      AND data -> 'track_metadata' -> 'additional_info' ->> 'recording_msid' = :recording_msid """

        try:
            with timescale.engine.connect() as connection:
                connection.execute(sqlalchemy.text(query), args)

            cache._r.decrby(cache._prep_key(REDIS_USER_LISTEN_COUNT + user_name))
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listen for user: %s" % str(e))
            raise TimescaleListenStoreException


class TimescaleListenStoreException(Exception):
    pass
