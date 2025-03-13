import subprocess
import tarfile
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional

import psycopg2
import psycopg2.sql
import sqlalchemy
import orjson
from brainzutils import cache
from psycopg2.errors import UntranslatableCharacter
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.db import timescale, DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listen import Listen
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION, LISTEN_MINIMUM_DATE
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, ORDER_DESC, DEFAULT_LISTENS_PER_FETCH
from listenbrainz.webserver import ts_conn

# Append the user name for both of these keys
REDIS_USER_LISTEN_COUNT = "lc."
REDIS_USER_TIMESTAMPS = "ts."
REDIS_TOTAL_LISTEN_COUNT = "lc-total"
# cache listen counts for 5 minutes only, so that listen counts are always up-to-date in 5 minutes.
REDIS_USER_LISTEN_COUNT_EXPIRY = 300

DUMP_CHUNK_SIZE = 100000
DATA_START_YEAR_IN_SECONDS = 1104537600

# How many listens to fetch on the first attempt. If we don't fetch enough, increase it by WINDOW_SIZE_MULTIPLIER
DEFAULT_FETCH_WINDOW = timedelta(days=30)  # 30 days

# When expanding the search, how fast should the bounds be moved out
WINDOW_SIZE_MULTIPLIER = 3

LISTEN_COUNT_BUCKET_WIDTH = 2592000

MAX_FUTURE_SECONDS = timedelta(minutes=10)  # max fwd clock skew
EPOCH = datetime.fromtimestamp(0, timezone.utc)


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
        ts_conn.execute(sqlalchemy.text(query), {"user_id": user_id})
        ts_conn.commit()

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

        query = "SELECT count, created FROM listen_user_metadata WHERE user_id = :user_id"
        result = ts_conn.execute(sqlalchemy.text(query), {"user_id": user_id})
        row = result.fetchone()
        if row:
            count, created = row.count, row.created
        else:
            # we can reach here only in tests, because we create entries in listen_user_metadata
            # table when user signs up and for existing users an entry should always exist.
            count, created = 0, LISTEN_MINIMUM_DATE

        cache.set(REDIS_USER_LISTEN_COUNT + str(user_id), count, REDIS_USER_LISTEN_COUNT_EXPIRY)
        return count

    def get_listen_count_for_users(self, user_ids: list):
        """Get the total number of listens for a list of users.

        Args:
            user_ids: the list of users to get listens for
        """
        cached_count_map = cache.get_many([REDIS_USER_LISTEN_COUNT + str(user_id) for user_id in user_ids])
        # Extract the user_ids for which we don't have cached counts. cached_cout is a dict of key-value pairs
        # where key is the cache key and value is the cached value. We need to extract the user_id from the cache key.
        listen_count = {int(key.split(".")[1]): value for key, value in cached_count_map.items()
                        if value is not None}
        missing_user_ids = set(user_ids) - set(listen_count.keys())

        if not missing_user_ids:
            return listen_count

        query = "SELECT user_id, count, created FROM listen_user_metadata WHERE user_id = ANY(:user_ids)"
        result = ts_conn.execute(sqlalchemy.text(query), {"user_ids": list(missing_user_ids)})
        data = result.fetchall()
        listen_count.update({row.user_id: row.count for row in data})
        cache.set_many({REDIS_USER_LISTEN_COUNT + str(row.user_id): row.count for row in data},
                       expirein=REDIS_USER_LISTEN_COUNT_EXPIRY)
        return listen_count


    def get_timestamps_for_user(self, user_id: int) -> Tuple[Optional[datetime], Optional[datetime]]:
        """ Return the min_ts and max_ts for the given list of users """
        query = """
            SELECT COALESCE(min_listened_at, 'epoch'::timestamptz) AS min_ts
                 , COALESCE(max_listened_at, 'epoch'::timestamptz) AS max_ts
              FROM listen_user_metadata
             WHERE user_id = :user_id
        """
        result = ts_conn.execute(text(query), {"user_id": user_id})
        row = result.fetchone()
        if row is None:
            min_ts = max_ts = EPOCH
        else:
            min_ts = row.min_ts
            max_ts = row.max_ts
        return min_ts, max_ts

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
                # psycopg2 returns the `value` as a DECIMAL type which is not recognized
                # by msgpack/redis. so cast to python int first.
                count = int(result.fetchone().value or 0)
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

        query = """
            WITH inserted_listens AS (
                INSERT INTO listen (listened_at, user_id, recording_msid, data)
                     VALUES %s
                ON CONFLICT (listened_at, user_id, recording_msid)
                 DO NOTHING
                  RETURNING listened_at, user_id, recording_msid
            ), metadata AS (
                INSERT INTO listen_user_metadata AS lum (user_id, count, min_listened_at, max_listened_at, created)
                     SELECT user_id, count(*), min(listened_at), max(listened_at), NOW()
                       FROM inserted_listens
                   GROUP BY user_id
                ON CONFLICT (user_id)
                  DO UPDATE
                        SET count = lum.count + excluded.count
                          , min_listened_at = least(lum.min_listened_at, excluded.min_listened_at)
                          , max_listened_at = greatest(lum.max_listened_at, excluded.max_listened_at)
                          , created = excluded.created
            ) SELECT * FROM inserted_listens
        """

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

        return inserted_rows

    def fetch_listens(self, user: Dict, from_ts: datetime = None, to_ts: datetime = None, limit: int = DEFAULT_LISTENS_PER_FETCH):
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

        if min_user_ts == EPOCH and max_user_ts == EPOCH:
            return [], min_user_ts, max_user_ts

        if to_ts is None and from_ts is None:
            to_ts = max_user_ts + timedelta(seconds=1)

        window_size = DEFAULT_FETCH_WINDOW
        query = """
                   WITH selected_listens AS (
                        SELECT l.listened_at
                             , l.created
                             , l.user_id
                             , l.recording_msid
                             , l.data
                             -- prefer to use user submitted mbid, then user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
                             , COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                          FROM listen l
                     LEFT JOIN mbid_mapping mm
                            ON l.recording_msid = mm.recording_msid
                     LEFT JOIN mbid_manual_mapping user_mm
                            ON l.recording_msid = user_mm.recording_msid
                           AND user_mm.user_id = l.user_id 
                     LEFT JOIN mbid_manual_mapping_top other_mm
                            ON l.recording_msid = other_mm.recording_msid
                         WHERE l.user_id = :user_id
                           AND listened_at > :from_ts
                           AND listened_at < :to_ts
                   )
                   SELECT listened_at
                        , user_id
                        , created
                        , sl.recording_msid::TEXT
                        , data
                        , sl.recording_mbid
                        , mbc.recording_data->>'name' AS recording_name
                        , mbc.release_mbid
                        , mbc.artist_mbids::TEXT[]
                        , (mbc.release_data->>'caa_id')::bigint AS caa_id
                        , mbc.release_data->>'caa_release_mbid' AS caa_release_mbid
                        , array_agg(artist->>'name' ORDER BY position) AS ac_names
                        , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases
                     FROM selected_listens sl
                LEFT JOIN mapping.mb_metadata_cache mbc
                       ON sl.recording_mbid = mbc.recording_mbid
        LEFT JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
                       ON TRUE
                 GROUP BY listened_at
                        , sl.recording_msid
                        , user_id
                        , created
                        , data
                        , sl.recording_mbid
                        , recording_data->>'name'
                        , release_mbid
                        , artist_mbids
                        , artist_data->>'name'
                        , recording_data->>'name'
                        , release_data->>'name'
                        , release_data->>'caa_id'
                        , release_data->>'caa_release_mbid'
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

        t0 = time.monotonic()

        passes = 0
        while True:
            passes += 1

            # Oh shit valve. I'm keeping it here for the time being. :)
            if passes == 10:
                done = True
                break

            curs = ts_conn.execute(
                sqlalchemy.text(query),
                {"user_id": user["id"], "from_ts": from_ts, "to_ts": to_ts, "limit": limit}
            )
            while True:
                result = curs.fetchone()
                if not result:
                    if not to_dynamic and not from_dynamic:
                        done = True
                        break

                    if from_ts < min_user_ts - timedelta(seconds=1):
                        done = True
                        break

                    if to_ts > datetime.now(tz=timezone.utc) + MAX_FUTURE_SECONDS:
                        done = True
                        break

                    if to_dynamic:
                        from_ts += window_size - timedelta(seconds=1)
                        window_size *= WINDOW_SIZE_MULTIPLIER
                        to_ts += window_size

                    if from_dynamic:
                        to_ts -= window_size
                        window_size *= WINDOW_SIZE_MULTIPLIER
                        from_ts -= window_size

                    break

                listens.append(Listen.from_timescale(
                    listened_at=result.listened_at,
                    user_id=result.user_id,
                    created=result.created,
                    recording_msid=result.recording_msid,
                    track_metadata=result.data,
                    recording_mbid=result.recording_mbid,
                    recording_name=result.recording_name,
                    release_mbid=result.release_mbid,
                    artist_mbids=result.artist_mbids,
                    ac_names=result.ac_names,
                    ac_join_phrases=result.ac_join_phrases,
                    user_name=user["musicbrainz_id"],
                    caa_id=result.caa_id,
                    caa_release_mbid=result.caa_release_mbid
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

    def fetch_recent_listens_for_users(self, users, min_ts: datetime = None, max_ts: datetime = None, per_user_limit=2, limit=10):
        """ Fetch recent listens for a list of users, given a limit which applies per user. If you
            have a limit of 3 and 3 users you should get 9 listens if they are available.

            user_ids: A list containing the users for which you'd like to retrieve recent listens.
            min_ts: Only return listens with listened_at after this timestamp
            max_ts: Only return listens with listened_at before this timestamp
            per_user_limit: the maximum number of listens for each user to fetch
            limit: the maximum number of listens overall to fetch
        """
        user_id_map = {user["id"]: user["musicbrainz_id"] for user in users}

        filters_list = ["user_id IN :user_ids"]
        args = {"user_ids": tuple(user_id_map.keys()), "per_user_limit": per_user_limit, "limit": limit}
        if min_ts:
            filters_list.append("listened_at > :min_ts")
            args["min_ts"] = min_ts
        if max_ts:
            filters_list.append("listened_at < :max_ts")
            args["max_ts"] = max_ts
        filters = " AND ".join(filters_list)

        query = f"""
              WITH intermediate AS (
                    SELECT listened_at
                         , created
                         , user_id
                         , recording_msid
                         , data
                         , row_number() OVER (PARTITION BY user_id ORDER BY listened_at DESC) AS rownum
                      FROM listen l
                     WHERE {filters} 
              ), selected_listens AS (
                    SELECT l.*
                        -- prefer to use user submitted mbid, then user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
                         , COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                      FROM intermediate l
                 LEFT JOIN mbid_mapping mm
                        ON l.recording_msid = mm.recording_msid
                 LEFT JOIN mbid_manual_mapping user_mm
                        ON l.recording_msid = user_mm.recording_msid
                       AND user_mm.user_id = l.user_id 
                 LEFT JOIN mbid_manual_mapping_top other_mm
                        ON l.recording_msid = other_mm.recording_msid
                     WHERE rownum <= :per_user_limit
              )     SELECT user_id
                         , listened_at
                         , created
                         , l.recording_msid::TEXT
                         , data
                         , l.recording_mbid
                         , mbc.recording_data->>'name' AS recording_name
                         , mbc.release_mbid
                         , mbc.artist_mbids::TEXT[]
                         , (mbc.release_data->>'caa_id')::bigint AS caa_id
                         , mbc.release_data->>'caa_release_mbid' AS caa_release_mbid
                         , array_agg(artist->>'name' ORDER BY position) AS ac_names
                         , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases            
                      FROM selected_listens l
                 LEFT JOIN mapping.mb_metadata_cache mbc
                        ON l.recording_mbid = mbc.recording_mbid
         LEFT JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
                        ON TRUE            
                  GROUP BY user_id
                         , listened_at
                         , l.recording_msid
                         , created
                         , data
                         , l.recording_mbid
                         , mbc.recording_data->>'name'
                         , mbc.release_mbid
                         , mbc.artist_mbids
                         , mbc.release_data->>'caa_id'
                         , mbc.release_data->>'caa_release_mbid'
                  ORDER BY listened_at DESC
                     LIMIT :limit
        """

        listens = []

        curs = ts_conn.execute(sqlalchemy.text(query), args)
        while True:
            result = curs.fetchone()
            if not result:
                break
            user_name = user_id_map[result.user_id]
            listens.append(Listen.from_timescale(
                listened_at=result.listened_at,
                user_id=result.user_id,
                created=result.created,
                recording_msid=result.recording_msid,
                track_metadata=result.data,
                recording_mbid=result.recording_mbid,
                recording_name=result.recording_name,
                release_mbid=result.release_mbid,
                artist_mbids=result.artist_mbids,
                ac_names=result.ac_names,
                ac_join_phrases=result.ac_join_phrases,
                user_name=user_name,
                caa_id=result.caa_id,
                caa_release_mbid=result.caa_release_mbid
            ))
        return listens

    def fetch_all_recent_listens_for_users(self, users, min_ts: datetime, max_ts: datetime, limit=25):
        """ Fetch recent listens for a list of users.

            users: A list containing the users for which you'd like to retrieve recent listens.
            min_ts: Only return listens with listened_at greater this timestamp, required.
            max_ts: Only return listens with listened_at lesser than this timestamp, required.
            limit: Listens returned per call. Should not exceed 100. Default value is 25, optional.
        """

        user_id_map = {user["id"]: user["musicbrainz_id"] for user in users}

        args = {"user_ids": tuple(user_id_map.keys()), "limit": limit}

        # min_ts and max_ts must exist.
        args["min_ts"] = min_ts
        args["max_ts"] = max_ts

        query = f"""
              WITH intermediate AS (
                    SELECT listened_at
                         , created
                         , user_id
                         , recording_msid
                         , data
                      FROM listen l
                     WHERE user_id IN :user_ids 
                       AND listened_at > :min_ts 
                       AND listened_at < :max_ts
              ), selected_listens AS (
                    SELECT l.*
                        -- prefer to use user submitted mbid, then user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
                         , COALESCE((data->'additional_info'->>'recording_mbid')::uuid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                      FROM intermediate l
                 LEFT JOIN mbid_mapping mm
                        ON l.recording_msid = mm.recording_msid
                 LEFT JOIN mbid_manual_mapping user_mm
                        ON l.recording_msid = user_mm.recording_msid
                       AND user_mm.user_id = l.user_id 
                 LEFT JOIN mbid_manual_mapping_top other_mm
                        ON l.recording_msid = other_mm.recording_msid
              )     SELECT user_id
                         , listened_at
                         , created
                         , l.recording_msid::TEXT
                         , data
                         , l.recording_mbid
                         , mbc.recording_data->>'name' AS recording_name
                         , mbc.release_mbid
                         , mbc.artist_mbids::TEXT[]
                         , (mbc.release_data->>'caa_id')::bigint AS caa_id
                         , mbc.release_data->>'caa_release_mbid' AS caa_release_mbid
                         , array_agg(artist->>'name' ORDER BY position) AS ac_names
                         , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases            
                      FROM selected_listens l
                 LEFT JOIN mapping.mb_metadata_cache mbc
                        ON l.recording_mbid = mbc.recording_mbid
         LEFT JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
                        ON TRUE            
                  GROUP BY user_id
                         , listened_at
                         , l.recording_msid
                         , created
                         , data
                         , l.recording_mbid
                         , mbc.recording_data->>'name'
                         , mbc.release_mbid
                         , mbc.artist_mbids
                         , mbc.release_data->>'caa_id'
                         , mbc.release_data->>'caa_release_mbid'
                  ORDER BY listened_at DESC
                    LIMIT :limit
        """

        listens = []

        curs = ts_conn.execute(sqlalchemy.text(query), args)
        while True:
            result = curs.fetchone()
            if not result:
                break
            user_name = user_id_map[result.user_id]
            listens.append(Listen.from_timescale(
                listened_at=result.listened_at,
                user_id=result.user_id,
                created=result.created,
                recording_msid=result.recording_msid,
                track_metadata=result.data,
                recording_mbid=result.recording_mbid,
                recording_name=result.recording_name,
                release_mbid=result.release_mbid,
                artist_mbids=result.artist_mbids,
                ac_names=result.ac_names,
                ac_join_phrases=result.ac_join_phrases,
                user_name=user_name,
                caa_id=result.caa_id,
                caa_release_mbid=result.caa_release_mbid
            ))

        return listens

    def import_listens_dump(self, archive_path: str, threads: int = DUMP_DEFAULT_THREAD_COUNT):
        """ Imports listens into TimescaleDB from a ListenBrainz listens dump .tar.zst archive.

        Args:
            archive_path: the path to the listens dump .tar.zst archive to be imported
            threads: the number of threads to be used for decompression
                        (defaults to DUMP_DEFAULT_THREAD_COUNT)

        Returns:
            int: the number of users for whom listens have been imported
        """

        self.log.info(
            'Beginning import of listens from dump %s...', archive_path)

        # construct the zstd command to decompress the archive
        zstd_command = ['zstd', '--decompress', '--stdout', archive_path, f'-T{threads}']
        zstd = subprocess.Popen(zstd_command, stdout=subprocess.PIPE)

        schema_checked = False
        total_imported = 0
        with tarfile.open(fileobj=zstd.stdout, mode='r|') as tar:
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
                        raise SchemaMismatchException("SCHEMA_SEQUENCE file missing FROM listen dump.")

                    # tarf, really? That's the name you're going with? Yep.
                    with tar.extractfile(member) as tarf:
                        while True:
                            line = tarf.readline()
                            if not line:
                                break

                            listen = Listen.from_json(orjson.loads(line))
                            listens.append(listen)

                            if len(listens) > DUMP_CHUNK_SIZE:
                                total_imported += len(listens)
                                self.insert(listens)
                                listens = []

            if len(listens) > 0:
                total_imported += len(listens)
                self.insert(listens)

        if not schema_checked:
            raise SchemaMismatchException("SCHEMA_SEQUENCE file missing FROM listen dump.")

        self.log.info('Import of listens from dump %s done!', archive_path)
        zstd.stdout.close()

        return total_imported

    def delete(self, user_id, created=None):
        """ Delete all listens for user with specified user ID.

        Note: this method tries to delete the user 5 times before giving up.

        Args:
            musicbrainz_id: the MusicBrainz ID of the user
            user_id: the listenbrainz row id of the user
            created: delete listens created before this timestamp

        Raises: Exception if unable to delete the user in 5 retries
        """
        if created is None:
            created = datetime.now(tz=timezone.utc)
        query1 = """
            UPDATE listen_user_metadata 
               SET count = 0
                 , min_listened_at = NULL
                 , max_listened_at = NULL
             WHERE user_id = :user_id
        """
        query2 = """DELETE FROM listen WHERE user_id = :user_id AND created <= :created"""
        query3 = """INSERT INTO deleted_user_listen_history (user_id, max_created) VALUES (:user_id, :created)"""
        try:
            ts_conn.execute(sqlalchemy.text(query1), {"user_id": user_id})
            ts_conn.execute(sqlalchemy.text(query2), {"user_id": user_id, "created": created})
            ts_conn.execute(sqlalchemy.text(query3), {"user_id": user_id, "created": created})
            ts_conn.commit()
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listens for user: %s" % str(e))
            raise

    def delete_listen(self, listened_at: datetime, user_id: int, recording_msid: str):
        """ Delete a particular listen for user with specified MusicBrainz ID.

        .. note::

            These details are stored in a separate table for some time because the listen is not deleted
            immediately. Every hour a cron job runs and uses these details to delete the actual listens.
            After the listens are deleted, these details are also removed from storage.

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
            ts_conn.execute(
                sqlalchemy.text(query),
                {"listened_at": listened_at, "user_id": user_id, "recording_msid": recording_msid}
            )
            ts_conn.commit()
        except psycopg2.OperationalError as e:
            self.log.error("Cannot delete listen for user: %s" % str(e))
            raise TimescaleListenStoreException()


class TimescaleListenStoreException(Exception):
    pass
