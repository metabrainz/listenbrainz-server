# coding=utf-8

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale
import os.path
import subprocess
import tarfile
import tempfile
import time
import shutil
import ujson
import uuid
import json
import psycopg2
from psycopg2.extras import execute_values
import sqlalchemy

from brainzutils import cache
from collections import defaultdict
from datetime import datetime, timezone

from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listen import Listen, convert_timescale_row_to_spark_row
from listenbrainz.listenstore import ListenStore
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, \
    USER_CACHE_TIME, REDIS_USER_TIMESTAMPS, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.utils import create_path, log_ioerrors, init_cache

REDIS_TIMESCALE_USER_LISTEN_COUNT = "ls.listencount."  # append username
DUMP_CHUNK_SIZE = 100000
NUMBER_OF_USERS_PER_DIRECTORY = 1000
DUMP_FILE_SIZE_LIMIT = 1024 * 1024 * 1024 # 1 GB


class TimescaleListenStore(ListenStore):

    REDIS_TIMESCALE_TOTAL_LISTEN_COUNT = "ls.listencount.total"
    TOTAL_LISTEN_COUNT_CACHE_TIME = 5 * 60
    USER_LISTEN_COUNT_CACHE_TIME = 10 * 60  # in seconds. 15 minutes

    def __init__(self, conf, logger):
        super(TimescaleListenStore, self).__init__(logger)

        timescale.init_db_connection(conf['SQLALCHEMY_TIMESCALE_URI'])

        # Initialize brainzutils cache
        init_cache(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'], namespace=conf['REDIS_NAMESPACE'])
        self.dump_temp_dir_root = conf.get('LISTEN_DUMP_TEMP_DIR_ROOT', tempfile.mkdtemp())

    def get_listen_count_for_user_from_timescale(self, user_name):
        """ Returns the listen count of a user from Timescale

            Args:
                user_name: the musicbrainz id of user whose listen count needs to be reset
        """
        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("SELECT SUM(count) FROM listen_count WHERE user_name = :user_name"), {
                    "user_name": user_name,
                })
                count = result.fetchone()[0] or 0

        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise

        return count

    def get_listen_count_for_user(self, user_name, need_exact=False):
        """Get the total number of listens for a user. The number of listens comes from
           brainzutils cache unless an exact number is asked for.

        Args:
            user_name: the user to get listens for
            need_exact: if True, get an exact number of listens directly from the ListenStore
        """

        if not need_exact:
            # check if the user's listen count is already in cache
            # if already present return it directly instead of calculating it again
            # decode is set to False as we have not encoded the value when we set it
            # in brainzutils cache as we need to call increment operation which requires
            # an integer value
            user_key = '{}{}'.format(REDIS_TIMESCALE_USER_LISTEN_COUNT, user_name)
            count = cache.get(user_key, decode=False)
            if count:
                return int(count)

        count = self.get_listen_count_for_user_from_timescale(user_name)

        # put this value into brainzutils cache with an expiry time
        user_key = "{}{}".format(REDIS_TIMESCALE_USER_LISTEN_COUNT, user_name)
        cache.set(user_key, count, TimescaleListenStore.USER_LISTEN_COUNT_CACHE_TIME, encode=False)
        return count


    def reset_listen_count(self, user_name):
        """ Reset the listen count of a user from cache and put in a new calculated value.

            Args:
                user_name: the musicbrainz id of user whose listen count needs to be reset
        """
        self.get_listen_count_for_user(user_name, need_exact=True)


    def _select_single_timestamp(self, select_min_timestamp, user_name):

        if select_min_timestamp:
            query = "SELECT min(listened_at) AS value FROM listen WHERE user_name = :user_name"
        else:
            query = "SELECT max(listened_at) AS value FROM listen WHERE user_name = :user_name"

        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query), {
                    "user_name": user_name
                })
                return result.fetchone()["value"]
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise


    def get_total_listen_count(self, cache_value=True):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the brainzutils cache for the value, if not present there
            makes a query to the db and caches it in brainzutils cache.
        """

        if cache_value:
            count = cache.get(TimescaleListenStore.REDIS_TIMESCALE_TOTAL_LISTEN_COUNT, decode=False)
            if count:
                return int(count)

        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("SELECT SUM(count) FROM listen_count"))
                count = result.fetchone()["sum"]
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise

        if cache_value:
            cache.set(
                TimescaleListenStore.REDIS_TIMESCALE_TOTAL_LISTEN_COUNT,
                count,
                TimescaleListenStore.TOTAL_LISTEN_COUNT_CACHE_TIME,
                encode=False,
            )
        return count


    def get_timestamps_for_user(self, user_name):
        """ Return the max_ts and min_ts for a given user and cache the result in brainzutils cache
        """

        tss = cache.get(REDIS_USER_TIMESTAMPS % user_name)
        if tss:
            (min_ts, max_ts) = tss.split(",")
            min_ts = int(min_ts)
            max_ts = int(max_ts)
        else:
            min_ts = self._select_single_timestamp(True, user_name)
            max_ts = self._select_single_timestamp(False, user_name)

            cache.set(REDIS_USER_TIMESTAMPS % user_name, "%d,%d" % (min_ts, max_ts), USER_CACHE_TIME)

        return min_ts, max_ts


    def insert(self, listens):
        """ 
            Insert a batch of listens. Returns a list of (listened_at, recording_msid, user_name) that indicates
            which rows were inserted into the DB. If the row is not listed in the return values, it was a duplicate.
        """

        submit = []
        for listen in listens:
            submit.append((listen.ts_since_epoch, listen.recording_msid, listen.user_name, listen.to_timescale()))

        query = """INSERT INTO listen (listened_at, recording_msid, user_name, data)
                    VALUES %s
                    ON CONFLICT (listened_at, recording_msid, user_name)
                        DO NOTHING
                        RETURNING listened_at, recording_msid, user_name"""

        try:
            inserted_rows = []
            conn = timescale.engine.raw_connection()
            with conn.cursor() as curs:
                execute_values(curs, query, submit, template=None)
                while True:
                    result = curs.fetchone()
                    if not result:
                        break
                    inserted_rows.append((result[0], result[1], result[2]))

            conn.commit()
        except psycopg2.OperationalError as err:
            self.log.error("Cannot write data to timescale: %s." % str(err))
            return 0

        # So update the listen counts of the users cached in brainzutils cache.
        for ts, msid, user_name in inserted_rows:
            user_key = "{}{}".format(REDIS_TIMESCALE_USER_LISTEN_COUNT, user_name)
            cached_count = cache.get(user_key, decode=False)
            if cached_count:
                cache.increment(user_key)

        # Invalidate cached data for user
        user_names = {}
        for user_name in user_names.keys():
            cache.delete(REDIS_USER_TIMESTAMPS % user_name)

        return inserted_rows


    # TODO: Fetch created from the DB as well
    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
        """

        query = 'SELECT listened_at, recording_msid, data FROM listen WHERE user_name = :user_name AND '
        if from_ts is not None:
            query += "listened_at > :ts"
            ts = from_ts
        else:
            query += "listened_at < :ts"
            ts = to_ts

        query += " ORDER BY listened_at " + ORDER_TEXT[order] + " LIMIT :limit"

        listens = []
        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query), user_name=user_name, ts=ts, limit=limit)
            while True:
                result = curs.fetchone()
                if not result:
                    break
            
                listens.append(Listen.from_timescale(result[0], result[1], user_name, result[2]))

        if order == ORDER_ASC:
            listens.reverse()

        return listens


    def fetch_recent_listens_for_users(self, user_list, limit = 2, max_age = 3600):
        """ Fetch recent listens for a list of users, given a limit which applies per user. If you
            have a limit of 3 and 3 users you should get 9 listens if they are available.

            user_list: A list containing the users for which you'd like to retrieve recent listens.
            limit: the maximum number of listens for each user to fetch.
            max_age: Only return listens if they are no more than max_age seconds old. Default 3600 seconds
        """

        args = { 'user_list' : tuple(user_list), 'ts' : int(time.time()) - max_age, 'limit' : limit }
        query = """SELECT * FROM (
                              SELECT listened_at, recording_msid, user_name, data,
                                     row_number() OVER (partition by user_name ORDER BY listened_at DESC) AS rownum
                                FROM listen
                               WHERE user_name IN :user_list
                                 AND listened_at > :ts
                            GROUP BY user_name, listened_at, recording_msid, data
                            ORDER BY listened_at DESC) tmp
                           WHERE rownum <= :limit"""
        print(max_age)
        print(query)
        print(args)

        listens = []
        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query), args)
            while True:
                result = curs.fetchone()
                if not result:
                    break
            
                print(Listen.from_timescale(result[0], result[1], result[2], result[3]))
                listens.append(Listen.from_timescale(result[0], result[1], result[2], result[3]))

        return listens


    def get_listens_query_for_dump(self, user_name, end_time, offset):
        """ 
            Get a query and its args dict to select a batch for listens for the full dump.
            Use listened_at timestamp, since not all listens have the created timestamp.
        """

        query = """SELECT listened_at, recording_msid, user_name, created, data
                     FROM listen
                    WHERE listened_at <= :ts
                      AND (created IS NULL OR created <= to_timestamp(:ts))
                      AND user_name = :user_name
                 ORDER BY listened_at DESC
                    LIMIT :limit
                   OFFSET :offset"""
        args = {
            'user_name' : user_name,
            'ts' : end_time,
            'offset' : offset,
            'limit' : DUMP_CHUNK_SIZE
        }

        return (query, args)


    def get_incremental_listens_query_batch(self, user_name, start_time, end_time, offset):
        """ 
            Get a query for a batch of listens for an incremental listen dump.
            This uses the `created` column to fetch listens.
        """

        query = """SELECT listened_at, recording_msid, user_name, created, data 
                     FROM listen
                    WHERE created > :start_ts
                      AND created <= :end_ts
                 ORDER BY created DESC
                    LIMIT :limit
                   OFFSET :offset"""

        args = {
            'user_name' : user_name,
            'start_ts' : start_time,
            'end_ts' : end_time,
            'offset' : offset,
            'limit' : DUMP_CHUNK_SIZE
        }
            
        return (query, args)


    def write_spark_listens_to_disk(self, listens, temp_dir):
        """ Write all spark listens in year/month dir format to disk.

        Args:
            listens : the listens to be written into the disk
            temp_dir: the dir into which listens should be written
        """
        for year in listens:
            for month in listens[year]:
                if year < 2002:
                    directory = temp_dir
                    filename = os.path.join(directory, 'invalid.json')
                else:
                    directory = os.path.join(temp_dir, str(year))
                    filename = os.path.join(directory, '{}.json'.format(str(month)))
                create_path(directory)
                with open(filename, 'a') as f:
                    f.write('\n'.join([ujson.dumps(listen) for listen in listens[year][month]]))
                    f.write('\n')


    def dump_user_for_spark(self, username, start_time, end_time, temp_dir):
        """ Dump listens for a particular user in the format for the ListenBrainz spark dump.

        Args:
            username (str): the MusicBrainz ID of the user
            start_time and end_time (datetime): the range of time for the listens dump.
            temp_dir (str): the dir to use to write files before adding to archive
        """
        t0 = time.time()
        offset = 0
        listen_count = 0

        unwritten_listens = {}

        while True:
            if start_time == datetime.utcfromtimestamp(0): # if we need a full dump
                query, args = self.get_listens_query_for_dump(username, int(end_time.strftime('%s')), offset)
            else:
                query, args = self.get_incremental_listens_query_batch(username, start_time, end_time, offset)

            rows_added = 0
            with timescale.engine.connect() as connection:
                curs = connection.execute(sqlalchemy.text(query), args)
                while True:
                    result = curs.fetchone()
                    if not result:
                        break
                
                    listen = convert_timescale_row_to_spark_row(result)
                    timestamp = listen['listened_at']

                    if timestamp.year not in unwritten_listens:
                        unwritten_listens[timestamp.year] = {}
                    if timestamp.month not in unwritten_listens[timestamp.year]:
                        unwritten_listens[timestamp.year][timestamp.month] = []

                    unwritten_listens[timestamp.year][timestamp.month].append(listen)
                    rows_added += 1

            if rows_added == 0:
                break

            listen_count += rows_added
            offset += DUMP_CHUNK_SIZE

        self.write_spark_listens_to_disk(unwritten_listens, temp_dir)
        self.log.info("%d listens for user %s dumped at %.2f listens / sec", listen_count, username, listen_count / (time.time() - t0))


    def dump_user(self, username, fileobj, start_time, end_time):
        """ Dump specified user's listens into specified file object.

        Args:
            username (str): the MusicBrainz ID of the user whose listens are to be dumped
            fileobj (file): the file into which listens should be written
            start_time and end_time (datetime): the range of time for which listens are to be dumped

        Returns:
            int: the number of bytes this user's listens take in the dump file
        """
        t0 = time.time()
        offset = 0
        bytes_written = 0
        listen_count = 0

        # Get this user's listens in chunks
        while True:
            if start_time == datetime.utcfromtimestamp(0):
                query, args = self.get_listens_query_for_dump(username, int(end_time.strftime('%s')), offset)
            else:
                query, args = self.get_incremental_listens_query_batch(username, start_time, end_time, offset)

            rows_added = 0
            with timescale.engine.connect() as connection:
                curs = connection.execute(sqlalchemy.text(query), args)
                while True:
                    result = curs.fetchone()
                    if not result:
                        break

                    listen = Listen.from_timescale(result[0], result[1], result[2], result[4]).to_api()
                    listen['user_name'] = username
                    print(listen)
                    try:
                        bytes_written += fileobj.write(ujson.dumps(listen))
                        bytes_written += fileobj.write('\n')
                        rows_added += 1
                    except IOError as e:
                        self.log.critical('IOError while writing listens into file for user %s', username, exc_info=True)
                        raise
                    except Exception as e:
                        self.log.error('Exception while creating json for user %s: %s', username, str(e), exc_info=True)
                        raise

            listen_count += rows_added
            if not rows_added:
                break

            offset += DUMP_CHUNK_SIZE

        time_taken = time.time() - t0
        self.log.info('Listens for user %s dumped, total %d listens written at %.2f listens / sec!',
            username, listen_count, listen_count / time_taken)

        # the size for this user should not include the last newline we wrote
        # hence return bytes_written - 1 as the size in the dump for this user
        return bytes_written - 1


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
                start_timestamp_path = os.path.join(temp_dir, 'START_TIMESTAMP')
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
            self.log.critical('IOError while writing metadata dump files: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            self.log.error('Exception while adding dump metadata: %s', str(e), exc_info=True)
            raise


    def write_listens_to_dump(self, listens_path, users, tar, archive_name, start_time, end_time):
        """ Write listens into the ListenBrainz dump.

        Args:
            listens_path (str): the path where listens should be kept before adding to the archive
            users (List[dict]): a list of all users
            tar (TarFile obj): the tar obj to which listens should be added
            archive_name (str): the name of the archive
            start_time and end_time: the range of time for which listens are to be dumped
        """
        dump_complete = False
        next_user_id = 0
        index = {}
        while not dump_complete:
            file_uuid = str(uuid.uuid4())
            file_name = file_uuid + '.listens'
            # directory structure of the form "/%s/%02s/%s.listens" % (uuid[0], uuid[0:2], uuid)
            file_directory = os.path.join(file_name[0], file_name[0:2])
            tmp_directory = os.path.join(listens_path, file_directory)
            create_path(tmp_directory)
            tmp_file_path = os.path.join(tmp_directory, file_name)
            archive_file_path = os.path.join(archive_name, 'listens', file_directory, file_name)
            with open(tmp_file_path, 'w') as f:
                file_done = False
                while next_user_id < len(users):
                    if f.tell() > DUMP_FILE_SIZE_LIMIT:
                        file_done = True
                        break

                    username = users[next_user_id]['musicbrainz_id']
                    offset = f.tell()
                    size = self.dump_user(username=username, fileobj=f, start_time=start_time, end_time=end_time)
                    index[username] = {
                        'file_name': file_uuid,
                        'offset': offset,
                        'size': size,
                    }
                    next_user_id += 1
                    self.log.info("%d users done. Total: %d", next_user_id, len(users))

            if file_done:
                tar.add(tmp_file_path, arcname=archive_file_path)
                os.remove(tmp_file_path)
                continue

            if next_user_id == len(users):
                if not file_done: # if this was the last user and file hasn't been added, add it
                    tar.add(tmp_file_path, arcname=archive_file_path)
                    os.remove(tmp_file_path)
                dump_complete = True
                break

        return index


    def write_listens_for_spark(self, listens_path, users, start_time, end_time):
        """ Write listens into the ListenBrainz spark dump.

        This is different from `write_listens_to_dump` because of the different format.

        Args:
            listens_path (str): the path where listens should be written before adding to the archive
            users (List[dict]): A list of all users
            start_time and end_time: the range of time for which listens are to be dumped
        """
        for i, user in enumerate(users):
            self.dump_user_for_spark(user['musicbrainz_id'], start_time, end_time, listens_path)
            self.log.info("%d users done. Total: %d", i + 1, len(users))


    def write_dump_index_file(self, index, temp_dir, tar, archive_name):
        """ Writes the ListenBrainz dump index file and adds it to the archive.

        Args:
            index (dict): the index to be written into the dump
            temp_dir (str): the temp dir where all files should be created initially
            tar (TarFile): the tarfile object into which the index file should be added
            archive_name (str): the name of the dump archive
        """
        try:
            index_path = os.path.join(temp_dir, 'index.json')
            with open(index_path, 'w') as f:
                f.write(ujson.dumps(index))
            tar.add(index_path,
                    arcname=os.path.join(archive_name, 'index.json'))
        except IOError as e:
            self.log.critical('IOError while writing index.json to archive: %s', str(e), exc_info=True)
            raise
        except Exception as e:
            self.log.error('Exception while adding index file to archive: %s', str(e), exc_info=True)
            raise


    def dump_listens(self, location, dump_id, start_time=datetime.utcfromtimestamp(0), end_time=None,
            threads=DUMP_DEFAULT_THREAD_COUNT, spark_format=False):
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
            threads (int): the number of threads to user for compression
            spark_format (bool): dump files in Apache Spark friendly format if True, else full dumps

        Returns:
            the path to the dump archive
        """

        if end_time is None:
            end_time = datetime.now()

        self.log.info('Beginning dump of listens from TimescaleDB...')

        self.log.info('Getting list of users whose listens are to be dumped...')
        users = db_user.get_all_users(columns=['id', 'musicbrainz_id'], created_before=end_time)
        self.log.info('Total number of users: %d', len(users))

        if start_time == datetime.utcfromtimestamp(0):
            full_dump = True
        else:
            full_dump = False

        archive_name = 'listenbrainz-listens-dump-{dump_id}-{time}'.format(dump_id=dump_id, time=end_time.strftime('%Y%m%d-%H%M%S'))
        if spark_format:
            archive_name = '{}-spark'.format(archive_name)

        if full_dump:
            archive_name = '{}-full'.format(archive_name)
        else:
            archive_name = '{}-incremental'.format(archive_name)
        archive_path = os.path.join(location, '{filename}.tar.xz'.format(filename=archive_name))
        with open(archive_path, 'w') as archive:

            pxz_command = ['pxz', '--compress', '-T{threads}'.format(threads=threads)]
            pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:

                temp_dir = os.path.join(self.dump_temp_dir_root, str(uuid.uuid4()))
                create_path(temp_dir)
                self.write_dump_metadata(archive_name, start_time, end_time, temp_dir, tar, full_dump)

                listens_path = os.path.join(temp_dir, 'listens')
                if spark_format:
                    self.write_listens_for_spark(listens_path, users, start_time, end_time)
                    tar.add(listens_path, arcname=os.path.join(archive_name, 'listens'))
                else:
                    index = self.write_listens_to_dump(listens_path, users, tar, archive_name, start_time, end_time)
                    self.write_dump_index_file(index, temp_dir, tar, archive_name)

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

        self.log.info('Beginning import of listens from dump %s...', archive_path)

        # construct the pxz command to decompress the archive
        pxz_command = ['pxz', '--decompress', '--stdout', archive_path, '-T{threads}'.format(threads=threads)]

        # run the command once to ensure schema version is correct
        # and load the index
        pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

        index = None
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            schema_check_done = False
            index_loaded = False
            for member in tar:
                file_name = member.name.split('/')[-1]
                if file_name == 'SCHEMA_SEQUENCE':
                    self.log.info('Checking if schema version of dump matches...')
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != LISTENS_DUMP_SCHEMA_VERSION:
                        raise SchemaMismatchException('Incorrect schema version! Expected: %d, got: %d.'
                                        'Please ensure that the data dump version matches the code version'
                                        'in order to import the data.'
                                        % (LISTENS_DUMP_SCHEMA_VERSION, schema_seq))
                    schema_check_done = True

                elif file_name == 'index.json':
                    with tar.extractfile(member) as f:
                        index = ujson.load(f)
                    index_loaded = True

                if schema_check_done and index_loaded:
                    self.log.info('Schema version matched and index.json loaded!')
                    self.log.info('Starting import of listens...')
                    break
            else:
                raise SchemaMismatchException('Metadata files missing in dump, please ensure that the dump file is valid.')


        # close pxz command and start over again, this time with the aim of importing all listens
        pxz.stdout.close()

        file_contents = defaultdict(list)
        for user, info in index.items():
            file_contents[info['file_name']].append({
                'user_name': user,
                'offset': info['offset'],
                'size': info['size'],
            })

        for file_name in file_contents:
            file_contents[file_name] = sorted(file_contents[file_name], key=lambda x: x['offset'])

        pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

        users_done = 0
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            for member in tar:
                file_name = member.name.split('/')[-1]
                if file_name.endswith('.listens'):

                    file_name = file_name[:-8]
                    with tar.extractfile(member) as f:
                        for user in file_contents[file_name]:
                            self.log.info('Importing user %s...', user['user_name'])
                            assert(f.tell() == user['offset'])
                            bytes_read = 0
                            listens = []
                            while bytes_read < user['size']:
                                line = f.readline()
                                bytes_read += len(line)
                                listen = Listen.from_json(ujson.loads(line))
                                listens.append(listen)

                                if len(listens) > DUMP_CHUNK_SIZE:
                                    self.insert(listens)
                                    listens = []

                            if len(listens) > 0:
                                self.insert(listens)

                            self.log.info('Import of user %s done!', user['user_name'])
                            users_done += 1

        self.log.info('Import of listens from dump %s done!', archive_path)
        pxz.stdout.close()
        return users_done


    def delete(self, musicbrainz_id):
        """ Delete all listens for user with specified MusicBrainz ID.

        Note: this method tries to delete the user 5 times before giving up.

        Args:
            musicbrainz_id (str): the MusicBrainz ID of the user

        Raises: Exception if unable to delete the user in 5 retries
        """

        args = { 'user_name' : musicbrainz_id }
        query = "DELETE FROM listen WHERE user_name = :user_name"

        try:
            with timescale.engine.connect() as connection:
                curs = connection.execute(sqlalchemy.text(query), args)
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listens for user: %s" % str(e))
            raise


class TimescaleListenStoreException(Exception):
    pass
