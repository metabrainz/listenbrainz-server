import subprocess
import tarfile
import time
from typing import Dict, Tuple, Optional

import psycopg2
import psycopg2.sql
import sqlalchemy
import ujson
from brainzutils import cache
from psycopg2.errors import UntranslatableCharacter
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.db import timescale, DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listen import Listen
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION, LISTEN_MINIMUM_DATE
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, ORDER_DESC, DEFAULT_LISTENS_PER_FETCH

# Append the user name for both of these keys
REDIS_USER_LISTEN_COUNT = "lc."
REDIS_USER_TIMESTAMPS = "ts."
REDIS_TOTAL_LISTEN_COUNT = "lc-total"
# cache listen counts for 5 minutes only, so that listen counts are always up-to-date in 5 minutes.
REDIS_USER_LISTEN_COUNT_EXPIRY = 300

DUMP_CHUNK_SIZE = 100000
DATA_START_YEAR = 2005
DATA_START_YEAR_IN_SECONDS = 1104537600

# How many listens to fetch on the first attempt. If we don't fetch enough, increase it by WINDOW_SIZE_MULTIPLIER
DEFAULT_FETCH_WINDOW = 30 * 86400  # 30 days

# When expanding the search, how fast should the bounds be moved out
WINDOW_SIZE_MULTIPLIER = 3

LISTEN_COUNT_BUCKET_WIDTH = 2592000

MAX_FUTURE_SECONDS = 600  # 10 mins in future - max fwd clock skew


class TimescaleListenStore:
    '''
        The listenstore implementation for the timescale DB.
    '''

    def __init__(self, logger):
        self.log = logger

    def set_empty_values_for_user(self, user_id: int):
        """When a user is created, set the timestamp keys and insert an entry in the listen count
         table so that we can avoid the expensive lookup for a brand new user."""
        query = """INSERT INTO listen_user_metadata VALUES (:user_id, 0, NULL, NULL, NOW())"""
        with timescale.engine.connect() as connection:
            connection.execute(sqlalchemy.text(query), user_id=user_id)

    def get_listen_count_for_user(self, user_id: int):
        """Get the total number of listens for a user.

         The number of listens comes from cache if available otherwise the get the
         listen count from the database. To get the listen count from the database,
         query listen_user_metadata table for the count and the timestamp till which we
         already have counted. Then scan the listens created later than that timestamp
         to get the remaining count. Add the two counts to get total listen count.

        Args:
            user_id: the user to get listens for
        """
        cached_count = cache.get(REDIS_USER_LISTEN_COUNT + str(user_id))
        if cached_count:
            return cached_count

        with timescale.engine.connect() as connection:
            query = "SELECT count, created FROM listen_user_metadata WHERE user_id = :user_id"
            result = connection.execute(sqlalchemy.text(query), user_id=user_id)
            row = result.fetchone()
            if row:
                count, created = row["count"], row["created"]
            else:
                # we can reach here only in tests, because we create entries in listen_user_metadata
                # table when user signs up and for existing users an entry should always exist.
                count, created = 0, LISTEN_MINIMUM_DATE

            query_remaining = """
                SELECT count(*) AS remaining_count
                  FROM listen
                 WHERE user_id = :user_id
                   AND created > :created
            """
            result = connection.execute(sqlalchemy.text(query_remaining),
                                        user_id=user_id,
                                        created=created)
            remaining_count = result.fetchone()["remaining_count"]

            total_count = count + remaining_count
            cache.set(REDIS_USER_LISTEN_COUNT + str(user_id), total_count, REDIS_USER_LISTEN_COUNT_EXPIRY)
            return total_count

    def get_timestamps_for_user(self, user_id: int) -> Tuple[Optional[int], Optional[int]]:
        """ Return the min_ts and max_ts for the given list of users """
        query = """
            SELECT COALESCE(min(min_listened_at), 0) AS min_ts
                 , COALESCE(max(max_listened_at), 0) AS max_ts
              FROM listen_user_metadata
             WHERE user_id = :user_id 
        """
        with timescale.engine.connect() as connection:
            result = connection.execute(text(query), user_id=user_id)
            row = result.fetchone()
            if row is None:
                return 0, 0
            return row["min_ts"], row["max_ts"]

    def get_total_listen_count(self):
        """ Returns the total number of listens stored in the ListenStore.
            First checks the brainzutils cache for the value, if not present there
            makes a query to the db and caches it in brainzutils cache.
        """
        count = cache.get(REDIS_TOTAL_LISTEN_COUNT)
        if count:
            return count

        query = "SELECT SUM(count) AS value FROM listen_user_metadata"
        try:
            with timescale.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text(query))
                count = result.fetchone()["value"] or 0
        except psycopg2.OperationalError:
            self.log.error("Cannot query listen counts:", exc_info=True)
            raise

        cache.set(REDIS_TOTAL_LISTEN_COUNT, count, expirein=REDIS_USER_LISTEN_COUNT_EXPIRY)
        return count

    def insert(self, listens):
        """
            Insert a batch of listens. Returns a list of (listened_at, track_name, user_name, user_id) that indicates
            which rows were inserted into the DB. If the row is not listed in the return values, it was a duplicate.
        """

        submit = []
        for listen in listens:
            submit.append(listen.to_timescale())

        query = """INSERT INTO listen (listened_at, track_name, user_name, user_id, data)
                        VALUES %s
                   ON CONFLICT (listened_at, track_name, user_id)
                    DO NOTHING
                     RETURNING listened_at, track_name, user_name, user_id"""

        inserted_rows = []
        conn = timescale.engine.raw_connection()
        with conn.cursor() as curs:
            try:
                execute_values(curs, query, submit, template=None)
                while True:
                    result = curs.fetchone()
                    if not result:
                        break
                    inserted_rows.append((result[0], result[1], result[2], result[3]))
            except UntranslatableCharacter:
                conn.rollback()
                return

        conn.commit()

        return inserted_rows

    def fetch_listens(self, user: Dict, from_ts: int = None, to_ts: int = None, limit: int = DEFAULT_LISTENS_PER_FETCH):
        """ The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            If neither from_ts nor to_ts is provided, the latest listens for the user are returned.
            Returns a tuple of (listens, min_user_timestamp, max_user_timestamp)

            from_ts: seconds since epoch, in float. if specified, listens will be returned in ascending order. otherwise
                listens will be returned in descending order
            to_ts: seconds since epoch, in float
            limit: the maximum number of items to return
        """
        if from_ts and to_ts and from_ts >= to_ts:
            raise ValueError("from_ts should be less than to_ts")
        if from_ts:
            order = ORDER_ASC
        else:
            order = ORDER_DESC

        min_user_ts, max_user_ts = self.get_timestamps_for_user(user["id"])

        if min_user_ts == 0 and max_user_ts == 0:
            return [], min_user_ts, max_user_ts

        if to_ts is None and from_ts is None:
            to_ts = max_user_ts + 1

        window_size = DEFAULT_FETCH_WINDOW
        query = """SELECT listened_at, track_name, user_id, created, data, mm.recording_mbid, release_mbid, artist_mbids
                     FROM listen
          FULL OUTER JOIN mbid_mapping mm
                       ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = mm.recording_msid
          FULL OUTER JOIN mbid_mapping_metadata m
                       ON mm.recording_mbid = m.recording_mbid
                    WHERE user_id = :user_id
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

                curs = connection.execute(sqlalchemy.text(query), user_id=user["id"],
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

                        if to_ts > int(time.time()) + MAX_FUTURE_SECONDS:
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

                    listens.append(Listen.from_timescale(
                        listened_at=result["listened_at"],
                        track_name=result["track_name"],
                        user_id=result["user_id"],
                        created=result["created"],
                        data=result["data"],
                        recording_mbid=result["recording_mbid"],
                        release_mbid=result["release_mbid"],
                        artist_mbids=result["artist_mbids"],
                        user_name=user["musicbrainz_id"]
                    ))

                    if len(listens) == limit:
                        done = True
                        break

                if done:
                    break

            fetch_listens_time = time.monotonic() - t0

        if order == ORDER_ASC:
            listens.reverse()

        self.log.info("fetch listens %s %.2fs (%d passes)" % (user["musicbrainz_id"], fetch_listens_time, passes))

        return listens, min_user_ts, max_user_ts

    def fetch_recent_listens_for_users(self, users, min_ts: int = None, max_ts: int = None, limit=2):
        """ Fetch recent listens for a list of users, given a limit which applies per user. If you
            have a limit of 3 and 3 users you should get 9 listens if they are available.

            user_ids: A list containing the users for which you'd like to retrieve recent listens.
            min_ts: Only return listens with listened_at after this timestamp
            max_ts: Only return listens with listened_at before this timestamp
            limit: the maximum number of listens for each user to fetch.
        """
        user_id_map = {user["id"]: user["musicbrainz_id"] for user in users}

        filters_list = ["user_id IN :user_ids"]
        args = {"user_ids": tuple(user_id_map.keys()), "limit": limit}
        if min_ts:
            filters_list.append("listened_at > :min_ts")
            args["min_ts"] = min_ts
        if max_ts:
            filters_list.append("listened_at < :max_ts")
            args["max_ts"] = max_ts
        filters = " AND ".join(filters_list)

        query = f"""SELECT * FROM (
                              SELECT listened_at, track_name, user_id, created, data, mm.recording_mbid, release_mbid, artist_mbids,
                                     row_number() OVER (partition by user_id ORDER BY listened_at DESC) AS rownum
                                FROM listen l
                     FULL OUTER JOIN mbid_mapping m
                                  ON (data->'track_metadata'->'additional_info'->>'recording_msid')::uuid = m.recording_msid
                     FULL OUTER JOIN mbid_mapping_metadata mm
                                  ON mm.recording_mbid = m.recording_mbid
                               WHERE {filters}
                            GROUP BY user_id, listened_at, track_name, created, data, mm.recording_mbid, release_mbid, artist_mbids
                            ORDER BY listened_at DESC) tmp
                               WHERE rownum <= :limit"""

        listens = []
        with timescale.engine.connect() as connection:
            curs = connection.execute(sqlalchemy.text(query), args)
            while True:
                result = curs.fetchone()
                if not result:
                    break
                user_name = user_id_map[result["user_id"]]
                listens.append(Listen.from_timescale(
                    listened_at=result["listened_at"],
                    track_name=result["track_name"],
                    user_id=result["user_id"],
                    created=result["created"],
                    data=result["data"],
                    recording_mbid=result["recording_mbid"],
                    release_mbid=result["release_mbid"],
                    artist_mbids=result["artist_mbids"],
                    user_name=user_name
                ))
        return listens

    def import_listens_dump(self, archive_path: str, threads: int = DUMP_DEFAULT_THREAD_COUNT):
        """ Imports listens into TimescaleDB from a ListenBrainz listens dump .tar.xz archive.

        Args:
            archive_path: the path to the listens dump .tar.xz archive to be imported
            threads: the number of threads to be used for decompression
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

    def delete(self, user_id):
        """ Delete all listens for user with specified user ID.

        Note: this method tries to delete the user 5 times before giving up.

        Args:
            musicbrainz_id: the MusicBrainz ID of the user
            user_id: the listenbrainz row id of the user

        Raises: Exception if unable to delete the user in 5 retries
        """
        query = """
            UPDATE listen_user_metadata 
               SET count = 0
                 , min_listened_at = NULL
                 , max_listened_at = NULL
             WHERE user_id = :user_id;
            DELETE FROM listen WHERE user_id = :user_id;
        """
        try:
            with timescale.engine.connect() as connection:
                connection.execute(sqlalchemy.text(query), user_id=user_id)
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listens for user: %s" % str(e))
            raise

    def delete_listen(self, listened_at: int, user_id: int, recording_msid: str):
        """ Delete a particular listen for user with specified MusicBrainz ID.
        Args:
            listened_at: The timestamp of the listen
            user_id: the listenbrainz row id of the user
            recording_msid: the MessyBrainz ID of the recording
        Raises: TimescaleListenStoreException if unable to delete the listen
        """
        query = """
            INSERT INTO listen_delete_metadata(user_id, listened_at, recording_msid) 
                 VALUES (:user_id, :listened_at, :recording_msid)
        """
        try:
            with timescale.engine.begin() as connection:
                connection.execute(sqlalchemy.text(query), listened_at=listened_at,
                                   user_id=user_id, recording_msid=recording_msid)
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listen for user: %s" % str(e))
            raise TimescaleListenStoreException


class TimescaleListenStoreException(Exception):
    pass
