# coding=utf-8

import listenbrainz.db.user as db_user
import os.path
import subprocess
import tarfile
import tempfile
import time
import shutil
import ujson
import uuid

from collections import defaultdict
from datetime import datetime
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from redis import Redis

from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listen import Listen
from listenbrainz.listenstore import ListenStore
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, \
    USER_CACHE_TIME, REDIS_USER_TIMESTAMPS, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.utils import quote, get_escaped_measurement_name, get_measurement_name, get_influx_query_timestamp, \
    convert_influx_nano_to_python_time, convert_python_time_to_nano_int, convert_to_unix_timestamp, \
    create_path, log_ioerrors

REDIS_INFLUX_USER_LISTEN_COUNT = "ls.listencount."  # append username
COUNT_RETENTION_POLICY = "one_week"
COUNT_MEASUREMENT_NAME = "listen_count"
TEMP_COUNT_MEASUREMENT = COUNT_RETENTION_POLICY + "." + COUNT_MEASUREMENT_NAME
TIMELINE_COUNT_MEASUREMENT = COUNT_MEASUREMENT_NAME

DUMP_CHUNK_SIZE = 100000

NUMBER_OF_USERS_PER_DIRECTORY = 1000
DUMP_FILE_SIZE_LIMIT = 1024 * 1024 * 1024 # 1 GB


class InfluxListenStore(ListenStore):

    REDIS_INFLUX_TOTAL_LISTEN_COUNT = "ls.listencount.total"
    TOTAL_LISTEN_COUNT_CACHE_TIME = 5 * 60
    USER_LISTEN_COUNT_CACHE_TIME = 10 * 60  # in seconds. 15 minutes

    def __init__(self, conf):
        ListenStore.__init__(self, conf)
        self.redis = Redis(host=conf['REDIS_HOST'], port=conf['REDIS_PORT'], decode_responses=True)
        self.redis.ping()
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
            results = self.influx.query('SELECT count(*) FROM ' + get_escaped_measurement_name(user_name))
        except (InfluxDBServerError, InfluxDBClientError) as e:
            self.log.error("Cannot query influx: %s" % str(e))
            raise

        # get the number of listens from the json
        try:
            count = results.get_points(measurement = get_measurement_name(user_name)).__next__()['count_recording_msid']
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
        except Exception as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        for result in results.get_points(measurement=measurement):
            return result['time']

        return None

    def _select_single_timestamp(self, query, measurement):
        try:
            results = self.influx.query(query)
        except Exception as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        for result in results.get_points(measurement=measurement):
            dt = datetime.strptime(result['time'], "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.strftime('%s'))

        return None

    def get_total_listen_count(self, cache=True):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the redis cache for the value, if not present there
            makes a query to the db and caches it in redis.
        """

        if cache:
            count = self.redis.get(InfluxListenStore.REDIS_INFLUX_TOTAL_LISTEN_COUNT)
            if count:
                return int(count)

        try:
            result = self.influx.query("""SELECT %s
                                            FROM "%s"
                                        ORDER BY time DESC
                                           LIMIT 1""" % (COUNT_MEASUREMENT_NAME, TIMELINE_COUNT_MEASUREMENT))
        except (InfluxDBServerError, InfluxDBClientError) as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        try:
            item = result.get_points(measurement=TIMELINE_COUNT_MEASUREMENT).__next__()
            count = int(item[COUNT_MEASUREMENT_NAME])
            timestamp = convert_to_unix_timestamp(item['time'])
        except (KeyError, ValueError, StopIteration):
            timestamp = 0
            count = 0

        # Now sum counts that have been added in the interval we're interested in
        try:
            result = self.influx.query("""SELECT sum(%s) as total
                                            FROM "%s"
                                           WHERE time > %s""" % (COUNT_MEASUREMENT_NAME, TEMP_COUNT_MEASUREMENT, get_influx_query_timestamp(timestamp)))
        except (InfluxDBServerError, InfluxDBClientError) as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        try:
            data = result.get_points(measurement=TEMP_COUNT_MEASUREMENT).__next__()
            count += int(data['total'])
        except StopIteration:
            pass

        if cache:
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
            query = 'SELECT first(artist_msid) FROM ' + get_escaped_measurement_name(user_name)
            min_ts = self._select_single_timestamp(query, get_measurement_name(user_name))

            query = 'SELECT last(artist_msid) FROM ' + get_escaped_measurement_name(user_name)
            max_ts = self._select_single_timestamp(query, get_measurement_name(user_name))

            self.redis.setex(REDIS_USER_TIMESTAMPS % user_name, "%d,%d" % (min_ts, max_ts), USER_CACHE_TIME)

        return min_ts, max_ts

    def insert(self, listens):
        """ Insert a batch of listens.
        """

        submit = []
        user_names = {}
        for listen in listens:
            user_names[listen.user_name] = 1
            submit.append(listen.to_influx(quote(listen.user_name)))

        if not self.influx.write_points(submit, time_precision='s'):
            self.log.error("Cannot write data to influx. (write_points returned False)")

        # If we reach this point, we were able to write the listens to the InfluxListenStore.
        # So update the listen counts of the users cached in redis.
        for data in submit:
            user_key = "{}{}".format(REDIS_INFLUX_USER_LISTEN_COUNT, data['fields']['user_name'])
            if self.redis.exists(user_key):
                self.redis.incr(user_key)

        # Invalidate cached data for user
        for user_name in user_names.keys():
            self.redis.delete(REDIS_USER_TIMESTAMPS % user_name)

        if len(listens):
            # Enter a measurement to count items inserted
            submit = [{
                'measurement': TEMP_COUNT_MEASUREMENT,
                'tags': {
                    COUNT_MEASUREMENT_NAME: len(listens)
                },
                'fields': {
                    COUNT_MEASUREMENT_NAME: len(listens)
                }
            }]
            try:
                if not self.influx.write_points(submit):
                    self.log.error("Cannot write listen cound to influx. (write_points returned False)")
            except (InfluxDBServerError, InfluxDBClientError, ValueError) as err:
                self.log.error("Cannot write data to influx: %s" % str(err))
                raise

    def update_listen_counts(self):
        """ This should be called every few seconds in order to sum up all of the listen counts
            in influx and write them to a single figure
        """

        # To update the current listen total, find when we last updated the timeline.
        try:
            result = self.influx.query("""SELECT %s
                                            FROM "%s"
                                        ORDER BY time DESC
                                           LIMIT 1""" % (COUNT_MEASUREMENT_NAME, TIMELINE_COUNT_MEASUREMENT))
        except (InfluxDBServerError, InfluxDBClientError) as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        try:
            item = result.get_points(measurement=TIMELINE_COUNT_MEASUREMENT).__next__()
            total = int(item[COUNT_MEASUREMENT_NAME])
            start_timestamp = convert_influx_nano_to_python_time(item['time'])
        except (KeyError, ValueError, StopIteration):
            total = 0
            start_timestamp = 0

        # Next, find the timestamp of the latest and greatest temp counts
        try:
            result = self.influx.query("""SELECT %s
                                            FROM "%s"
                                        ORDER BY time DESC
                                           LIMIT 1""" % (COUNT_MEASUREMENT_NAME, TEMP_COUNT_MEASUREMENT))
        except (InfluxDBServerError, InfluxDBClientError) as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        try:
            item = result.get_points(measurement=TEMP_COUNT_MEASUREMENT).__next__()
            end_timestamp = convert_influx_nano_to_python_time(item['time'])
        except (KeyError, StopIteration):
            end_timestamp = start_timestamp

        # Now sum counts that have been added in the interval we're interested in
        try:
            result = self.influx.query("""SELECT sum(%s) as total
                                            FROM "%s"
                                           WHERE time > %d and time <= %d""" % (COUNT_MEASUREMENT_NAME, TEMP_COUNT_MEASUREMENT,
                                       convert_python_time_to_nano_int(start_timestamp), convert_python_time_to_nano_int(end_timestamp)))
        except (InfluxDBServerError, InfluxDBClientError) as err:
            self.log.error("Cannot query influx: %s" % str(err))
            raise

        try:
            data = result.get_points(measurement=TEMP_COUNT_MEASUREMENT).__next__()
            total += int(data['total'])
        except StopIteration:
            # This means we have no item_counts to update, so bail.
            return

        # Finally write a new total with the timestamp of the last point
        submit = [{
            'measurement': TIMELINE_COUNT_MEASUREMENT,
            'time': end_timestamp,
            'tags': {
                COUNT_MEASUREMENT_NAME: total
            },
            'fields': {
                COUNT_MEASUREMENT_NAME: total
            }
        }]

        try:
            if not self.influx.write_points(submit):
                self.log.error("Cannot write data to influx. (write_points returned False)")
        except (InfluxDBServerError, InfluxDBClientError, ValueError) as err:
            self.log.error("Cannot update listen counts in influx: %s" % str(err))
            raise

    def fetch_listens_from_storage(self, user_name, from_ts, to_ts, limit, order):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            from_ts: seconds since epoch, in float
            to_ts: seconds since epoch, in float
        """

        # Quote single quote characters which could be used to mount an injection attack.
        # Sadly, influxdb does not provide a means to do this in the client library
        query = 'SELECT * FROM ' + get_escaped_measurement_name(user_name)

        if from_ts is not None:
            query += "WHERE time > " + get_influx_query_timestamp(from_ts)
        else:
            query += "WHERE time < " + get_influx_query_timestamp(to_ts)

        query += " ORDER BY time " + ORDER_TEXT[order] + " LIMIT " + str(limit)
        try:
            results = self.influx.query(query)
        except Exception as err:
            self.log.error("Cannot query influx: %s" % str(err))
            return []

        listens = []
        for result in results.get_points(measurement=get_measurement_name(user_name)):
            listens.append(Listen.from_influx(result))

        if order == ORDER_ASC:
            listens.reverse()

        return listens


    def dump_user(self, username, fileobj, dump_time):
        """ Dump specified user's listens into specified file object.

        Args:
            username (str): the MusicBrainz ID of the user whose listens are to be dumped
            fileobj (file): the file into which listens should be written
            dump_time (datetime): the time at which the specific data dump was initiated

        Returns:
            int: the number of bytes written to the file
        """
        offset = 0
        bytes_written = 0
        # Get this user's listens in chunks
        while True:
            # loop until we get this chunk of listens
            while True:
                try:
                    result = self.influx.query("""
                        SELECT *
                          FROM {measurement}
                         WHERE time <= {timestamp}
                      ORDER BY time DESC
                         LIMIT {limit}
                        OFFSET {offset}
                    """.format(
                        measurement=get_escaped_measurement_name(username),
                        timestamp=get_influx_query_timestamp(dump_time.strftime('%s')),
                        limit=DUMP_CHUNK_SIZE,
                        offset=offset,
                    ))
                    break
                except Exception as e:
                    self.log.error('Error while getting listens for user %s', user['musicbrainz_id'])
                    self.log.error(str(e))
                    time.sleep(3)

            rows_added = 0
            for row in result.get_points(get_measurement_name(username)):
                listen = Listen.from_influx(row).to_api()
                try:
                    bytes_written += fileobj.write(ujson.dumps(listen))
                    bytes_written += fileobj.write('\n')
                    rows_added += 1
                except IOError as e:
                    log_ioerrors(self.log, e)
                    raise
                except Exception as e:
                    self.log.error('Exception while creating json for user: %s', user['musicbrainz_id'])
                    self.log.error(str(e))
                    raise

            if not rows_added:
                break

            offset += DUMP_CHUNK_SIZE

        return bytes_written

    def dump_listens(self, location, dump_time=datetime.today(), threads=None):
        """ Dumps all listens in the ListenStore into a .tar.xz archive.

        Files are created with UUIDs as names. Each file can contain listens for a number of users.
        An index.json file is used to save which file contains the listens of which users.

        Args:
            location: the directory where the listens dump archive should be created
            dump_time (datetime): the time at which the data dump was started
            threads (int): the number of threads to user for compression

        Returns:
            the path to the dump archive
        """

        self.log.info('Beginning dump of listens from InfluxDB...')

        self.log.info('Getting list of users whose listens are to be dumped...')
        users = db_user.get_all_users(columns=['id', 'musicbrainz_id'])
        self.log.info('Total number of users: %d', len(users))

        archive_name = 'listenbrainz-listens-dump-{time}'.format(time=dump_time.strftime('%Y%m%d-%H%M%S'))
        archive_path = os.path.join(location, '{filename}.tar.xz'.format(filename=archive_name))
        with open(archive_path, 'w') as archive:

            pxz_command = ['pxz', '--compress']
            if threads is not None:
                pxz_command.append('-T {threads}'.format(threads=threads))

            pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:

                temp_dir = tempfile.mkdtemp()

                try:
                    # add timestamp
                    timestamp_path = os.path.join(temp_dir, 'TIMESTAMP')
                    with open(timestamp_path, 'w') as f:
                        f.write(dump_time.isoformat(' '))
                    tar.add(timestamp_path,
                            arcname=os.path.join(archive_name, 'TIMESTAMP'))

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
                    log_ioerrors(self.log, e)
                    raise
                except Exception as e:
                    self.log.error('Exception while adding dump metadata: %s', str(e))
                    raise

                listens_path = os.path.join(temp_dir, 'listens')

                dump_complete = False
                next_user_id = 0
                index = {}
                while not dump_complete:
                    file_name = str(uuid.uuid4())
                    # directory structure of the form "/%s/%02s/%s.listens" % (uuid[0], uuid[0:2], uuid)
                    directory = os.path.join(listens_path, file_name[0], file_name[0:2])
                    create_path(directory)
                    file_path = os.path.join(directory, '{uuid}.listens'.format(uuid=file_name))
                    with open(file_path, 'w') as f:
                        file_done = False
                        while next_user_id < len(users):
                            if f.tell() > DUMP_FILE_SIZE_LIMIT:
                                file_done = True
                                break

                            username = users[next_user_id]['musicbrainz_id']
                            offset = f.tell()
                            size = self.dump_user(username=username, fileobj=f, dump_time=dump_time)
                            index[username] = {
                                'file_name': file_name,
                                'offset': offset,
                                'size': size,
                            }
                            next_user_id += 1

                        if file_done:
                            continue

                        if next_user_id == len(users):
                            dump_complete = True
                            break


                # add the listens directory to the archive
                self.log.info('Got all listens, adding them to the archive...')
                tar.add(listens_path,
                        arcname=os.path.join(archive_name, 'listens'))

                # add index.json file to the archive
                try:
                    index_path = os.path.join(temp_dir, 'index.json')
                    with open(index_path, 'w') as f:
                        f.write(ujson.dumps(index))
                    tar.add(index_path,
                            arcname=os.path.join(archive_name, 'index.json'))
                except IOError as e:
                    log_ioerrors(self.log, e)
                    raise
                except Exception as e:
                    self.log.error('Exception while adding index file to archive: %s', str(e))
                    raise

                # remove the temporary directory
                shutil.rmtree(temp_dir)

            pxz.stdin.close()

        self.log.info('ListenBrainz listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path


    def import_listens_dump(self, archive_path, threads=None):
        """ Imports listens into InfluxDB from a ListenBrainz listens dump .tar.xz archive.

        Args:
            archive (str): the path to the listens dump .tar.xz archive to be imported
            threads (int): the number of threads to be used for decompression (defaults to 1)

        Returns:
            int: the number of users for whom listens have been imported
        """

        self.log.info('Beginning import of listens from dump %s...', archive_path)

        # construct the pxz command to decompress the archive
        pxz_command = ['pxz', '--decompress', '--stdout', archive_path]
        if threads is not None:
            pxz_command.append('-T {threads}'.format(threads=threads))


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
                                listen = Listen.from_json(ujson.loads(line)).to_influx(quote(user['user_name']))
                                listens.append(listen)

                                if len(listens) > DUMP_CHUNK_SIZE:
                                    self.write_points_to_db(listens)
                                    listens = []

                            if len(listens) > 0:
                                self.write_points_to_db(listens)

                            self.log.info('Import of user %s done!', user['user_name'])
                            users_done += 1

        self.log.info('Import of listens from dump %s done!', archive_path)
        pxz.stdout.close()
        return users_done


    def write_points_to_db(self, points):
        """ Write the given data to InfluxDB. This function sleeps for 3 seconds
            and tries again if the write fails.

        Args:
            points: a list containing dicts in the form taken by influx python bindings
        """

        while not self.influx.write_points(points, time_precision='s'):
            self.log.error('Error while writing listens to influx, '
                'write_points returned False')
            time.sleep(3)
