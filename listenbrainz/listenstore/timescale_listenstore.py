import subprocess
import tarfile
import time
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional

import orjson
import psycopg2
import psycopg2.sql
import sqlalchemy
from brainzutils import cache
from psycopg2.errors import UntranslatableCharacter
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz.db import listens as listens_db, timescale
from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.dumps.exceptions import SchemaMismatchException
from listenbrainz.listen import Listen
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore import ORDER_ASC, ORDER_TEXT, ORDER_DESC, DEFAULT_LISTENS_PER_FETCH
from listenbrainz.webserver.listens_cache import get_listens_from_cache, set_listens_in_cache

# Append the user name for both of these keys
REDIS_USER_LISTEN_COUNT = "lc."
REDIS_USER_TIMESTAMPS = "ts."
REDIS_TOTAL_LISTEN_COUNT = "lc-total"
# cache listen counts for 5 minutes only, so that listen counts are always up-to-date in 5 minutes.
REDIS_USER_LISTEN_COUNT_EXPIRY = 300

DUMP_CHUNK_SIZE = 100000
DATA_START_YEAR_IN_SECONDS = 1104537600

LISTEN_COUNT_BUCKET_WIDTH = 2592000

EPOCH = datetime.fromtimestamp(0, timezone.utc)

LISTEN_COLUMNS_QUERY = """
    SELECT listened_at
         , created
         , user_id
         , recording_msid::TEXT
         , data
         , (data->'additional_info'->>'recording_mbid')::UUID::TEXT AS submitted_mbid
"""

# Listen.from_timescale arguments resolved by _fetch_mapping_metadata
MAPPING_METADATA_FIELDS = (
    "recording_mbid", "recording_name", "release_mbid", "release_group_mbid", "artist_mbids",
    "ac_names", "ac_join_phrases", "caa_id", "caa_release_mbid", "url_rels",
)


def _listens_engine():
    if listens_db.engine is None:
        raise ListenStoreException("Listens database is required to read listens")
    return listens_db.engine


class TimescaleListenStore:
    '''
        The listenstore implementation for the timescale DB.
    '''

    def __init__(self, logger):
        self.log = logger

    def set_empty_values_for_user(self, user_id: int):
        """When a user is created, insert an entry in the listen count table. If the user already
         has an entry, leave it unchanged.

         Skipped without the listens DB: the user was already created and a missing entry reads
         as zero listens, the first listen creates it."""
        if listens_db.engine is None:
            self.log.warning("Listens database is not configured, not creating listen count for user %d", user_id)
            return
        listens_db.add_missing_to_listen_user_metadata([user_id])

    def get_listen_count_for_user(self, user_id: int):
        """Get the total number of listens for a user.

         The number of listens comes from cache if available otherwise from the listen_user_metadata
         table in the listens database, which is kept up to date on ingestion and deletion.

        Args:
            user_id: the user to get listens for
        """
        cached_count = cache.get(REDIS_USER_LISTEN_COUNT + str(user_id))
        if cached_count:
            return cached_count

        query = "SELECT count FROM listen_user_metadata WHERE user_id = :user_id"
        with _listens_engine().connect() as connection:
            count = connection.execute(sqlalchemy.text(query), {"user_id": user_id}).scalar()
        if count is None:
            # users get an entry on sign up or with their first listen
            count = 0

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

        query = "SELECT user_id, count FROM listen_user_metadata WHERE user_id = ANY(:user_ids)"
        with _listens_engine().connect() as connection:
            data = connection.execute(sqlalchemy.text(query), {"user_ids": list(missing_user_ids)}).fetchall()
        listen_count.update({row.user_id: row.count for row in data})
        cache.set_many({REDIS_USER_LISTEN_COUNT + str(row.user_id): row.count for row in data},
                       expirein=REDIS_USER_LISTEN_COUNT_EXPIRY)
        return listen_count

    def get_timestamps_for_user(self, user_id: int) -> Tuple[Optional[datetime], Optional[datetime]]:
        """ Return the min_ts and max_ts of the user's listens, EPOCH if the user has none """
        query = """
            SELECT COALESCE(min_listened_at, 'epoch'::timestamptz) AS min_ts
                 , COALESCE(max_listened_at, 'epoch'::timestamptz) AS max_ts
              FROM listen_user_metadata
             WHERE user_id = :user_id
        """
        with _listens_engine().connect() as connection:
            row = connection.execute(text(query), {"user_id": user_id}).fetchone()
        if row is None:
            return EPOCH, EPOCH
        return row.min_ts, row.max_ts

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
            with _listens_engine().connect() as connection:
                result = connection.execute(sqlalchemy.text(query))
                # psycopg2 returns the `value` as a DECIMAL type which is not recognized
                # by msgpack/redis. so cast to python int first.
                count = int(result.fetchone().value or 0)
        except sqlalchemy.exc.OperationalError:
            self.log.error("Cannot query listen counts:", exc_info=True)
            raise

        cache.set(REDIS_TOTAL_LISTEN_COUNT, count, expirein=REDIS_USER_LISTEN_COUNT_EXPIRY)
        return count

    def insert(self, listens):
        """
            Insert a batch of listens. Returns a list of (listened_at, user_id, recording_msid)
            identifying rows inserted into the listens DB, which serves reads and counts. Rows
            absent from the result were duplicates there, even if Timescale inserted them
            (e.g. listens re-imported after a history deletion, which Timescale retains).
        """

        if not listens:
            return []

        submit = []
        created = datetime.now(tz=timezone.utc)
        for listen in listens:
            listened_at, user_id, recording_msid, data = listen.to_timescale()
            submit.append((listened_at, created, user_id, recording_msid, data))

        # Write Timescale before the listens DB, whose result is returned. Both stores ignore
        # duplicates, so if the listens DB write fails the retry still reports its new listens.
        # The reverse order would report nothing on a retry after a Timescale failure.
        query = """
            INSERT INTO listen (listened_at, created, user_id, recording_msid, data)
                 VALUES %s
            ON CONFLICT (listened_at, user_id, recording_msid)
             DO NOTHING
        """
        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                execute_values(
                    curs,
                    query,
                    submit,
                    template="(%s::timestamptz, %s::timestamptz, %s::integer, %s::uuid, %s::jsonb)",
                )
            conn.commit()
        except UntranslatableCharacter:
            # only skip the Timescale copy for its own encoding errors, the listens DB write
            # below must still succeed or fail the batch
            conn.rollback()
            self.log.warning("Skipping Timescale insert of batch with untranslatable characters", exc_info=True)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return listens_db.insert(submit)

    def _fetch_mapping_metadata(self, rows, conn) -> dict:
        """ Resolve the recording mbid and its MusicBrainz metadata for the given listens database rows.

            Returns a dict keyed on (user_id, recording_msid, submitted_mbid). has_metadata is false
            for listens whose recording is not in the metadata cache.

            conn: listens database connection
        """
        if not rows:
            return {}

        keys = {(row.user_id, row.recording_msid, row.submitted_mbid) for row in rows}
        user_ids, recording_msids, submitted_mbids = zip(*keys)

        query = """
              WITH listens (user_id, recording_msid, submitted_mbid) AS (
                    SELECT *
                      FROM unnest(CAST(:user_ids AS INTEGER[]), CAST(:recording_msids AS UUID[]), CAST(:submitted_mbids AS UUID[]))
              ), selected_listens AS (
                    SELECT l.user_id
                         , l.recording_msid
                         , l.submitted_mbid
                         -- prefer to use user submitted mbid, then user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
                         , COALESCE(l.submitted_mbid, user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS recording_mbid
                      FROM listens l
                 LEFT JOIN mapping.mbid_mapping mm
                        ON l.recording_msid = mm.recording_msid
                 LEFT JOIN mapping.mbid_manual_mapping user_mm
                        ON l.recording_msid = user_mm.recording_msid
                       AND user_mm.user_id = l.user_id
                 LEFT JOIN mapping.mbid_manual_mapping_top other_mm
                        ON l.recording_msid = other_mm.recording_msid
              )     SELECT sl.user_id
                         , sl.recording_msid::TEXT
                         , sl.submitted_mbid::TEXT
                         , sl.recording_mbid
                         , mbc.recording_data->>'name' AS recording_name
                         , mbc.release_mbid
                         , mbc.release_data->>'release_group_mbid' AS release_group_mbid
                         , mbc.artist_mbids::TEXT[]
                         , (mbc.release_data->>'caa_id')::bigint AS caa_id
                         , mbc.release_data->>'caa_release_mbid' AS caa_release_mbid
                         , mbc.recording_data->'url_rels' AS url_rels
                         , array_agg(artist->>'name' ORDER BY position) AS ac_names
                         , array_agg(artist->>'join_phrase' ORDER BY position) AS ac_join_phrases
                         , bool_or(mbc.recording_mbid IS NOT NULL) AS has_metadata
                      FROM selected_listens sl
                 LEFT JOIN mapping.mb_metadata_cache mbc
                        ON sl.recording_mbid = mbc.recording_mbid
         LEFT JOIN LATERAL jsonb_array_elements(artist_data->'artists') WITH ORDINALITY artists(artist, position)
                        ON TRUE
                  GROUP BY sl.user_id
                         , sl.recording_msid
                         , sl.submitted_mbid
                         , sl.recording_mbid
                         , mbc.recording_data->>'name'
                         , mbc.release_mbid
                         , mbc.release_data->>'release_group_mbid'
                         , mbc.artist_mbids
                         , mbc.release_data->>'caa_id'
                         , mbc.release_data->>'caa_release_mbid'
                         , mbc.recording_data->'url_rels'
        """
        result = conn.execute(sqlalchemy.text(query), {
            "user_ids": list(user_ids),
            "recording_msids": list(recording_msids),
            "submitted_mbids": list(submitted_mbids),
        })
        return {(row.user_id, row.recording_msid, row.submitted_mbid): row for row in result}

    def _listens_from_rows(self, connection, rows, user_id_map: Dict[int, str]):
        """ Convert rows fetched from the listens database into Listen objects, adding mapping metadata """
        metadata = self._fetch_mapping_metadata(rows, connection)
        listens = []
        for row in rows:
            meta = metadata.get((row.user_id, row.recording_msid, row.submitted_mbid))
            mapping = {field: getattr(meta, field, None) for field in MAPPING_METADATA_FIELDS}
            listens.append(Listen.from_timescale(
                listened_at=row.listened_at,
                user_id=row.user_id,
                created=row.created,
                recording_msid=row.recording_msid,
                track_metadata=row.data,
                user_name=user_id_map[row.user_id],
                **mapping
            ))
        return listens

    def fetch_listens(
        self,
        user: Dict,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
        limit: int = DEFAULT_LISTENS_PER_FETCH
    ):
        """ Retrieve a user's listens from the listens database.

            The timestamps are stored as UTC in the postgres datebase while on retrieving
            the value they are converted to the local server's timezone. So to compare
            datetime object we need to create a object in the same timezone as the server.

            If neither from_ts nor to_ts is provided, the latest listens for the user are returned.

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

        filters = ["user_id = :user_id"]
        if from_ts is not None:
            filters.append("listened_at > :from_ts")
        if to_ts is not None:
            filters.append("listened_at < :to_ts")

        query = LISTEN_COLUMNS_QUERY + """
                  FROM listen
                 WHERE """ + " AND ".join(filters) + """
              ORDER BY listened_at """ + ORDER_TEXT[order] + " LIMIT :limit"

        t0 = time.monotonic()

        with _listens_engine().connect() as connection:
            rows = connection.execute(
                sqlalchemy.text(query),
                {"user_id": user["id"], "from_ts": from_ts, "to_ts": to_ts, "limit": limit}
            ).fetchall()
            listens = self._listens_from_rows(connection, rows, {user["id"]: user["musicbrainz_id"]})

        fetch_listens_time = time.monotonic() - t0

        if order == ORDER_ASC:
            listens.reverse()

        self.log.info("fetch listens %s %.2fs" % (user["musicbrainz_id"], fetch_listens_time))

        return listens

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
                      FROM listen
                     WHERE {filters}
              ) {LISTEN_COLUMNS_QUERY}
                      FROM intermediate
                     WHERE rownum <= :per_user_limit
                  ORDER BY listened_at DESC
                     LIMIT :limit
        """

        with _listens_engine().connect() as connection:
            rows = connection.execute(sqlalchemy.text(query), args).fetchall()
            return self._listens_from_rows(connection, rows, user_id_map)

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

        query = LISTEN_COLUMNS_QUERY + """
                  FROM listen
                 WHERE user_id IN :user_ids
                   AND listened_at > :min_ts
                   AND listened_at < :max_ts
              ORDER BY listened_at DESC
                 LIMIT :limit
        """

        with _listens_engine().connect() as connection:
            rows = connection.execute(sqlalchemy.text(query), args).fetchall()
            return self._listens_from_rows(connection, rows, user_id_map)

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

    def fetch_listens_with_cache(
        self, user: dict, from_ts: datetime = None,
        to_ts: datetime = None, limit: int = DEFAULT_LISTENS_PER_FETCH
    ):
        """ Fetch listens for a user, using a cache to avoid unnecessary queries. If a database query is necessary,
            the result is cached.
        """
        key_parts = {
            "user_id": user["id"],
            "min_ts": int(from_ts.timestamp()) if from_ts else None,
            "max_ts": int(to_ts.timestamp()) if to_ts else None,
            "count": limit
        }
        cached_data = get_listens_from_cache(**key_parts)
        if cached_data is not None:
            return cached_data

        listens = self.fetch_listens(user, from_ts, to_ts, limit)
        min_ts_per_user, max_ts_per_user = self.get_timestamps_for_user(user["id"])
        listen_data = [listen.to_api() for listen in listens]
        data = {
            "count": len(listen_data),
            "listens": listen_data,
            "latest_listen_ts": int(max_ts_per_user.timestamp()),
            "oldest_listen_ts": int(min_ts_per_user.timestamp()),
        }

        set_listens_in_cache(data, **key_parts)

        return data

    def delete(self, user_id, created=None):
        """Delete history only in the listens DB, retaining Timescale listens and metadata."""
        # Keep the existing listenstore interface during migration; deletion and listen reads
        # use the listens DB while ingestion still writes to both.
        if created is None:
            created = datetime.now(tz=timezone.utc)
        listens_db.delete_user(user_id, created)

    def delete_listen(self, listened_at: datetime, user_id: int, recording_msid: str):
        """ Delete a particular listen for user with specified MusicBrainz ID.

        .. note::

            These details are stored in a separate table for some time because the listen is not deleted
            immediately. Every hour a cron job runs and uses these details to delete the actual listens.
            The request and its result are retained in the listens database until dump cleanup.

        Args:
            listened_at: The timestamp of the listen
            user_id: the listenbrainz row id of the user
            recording_msid: the MessyBrainz ID of the recording
        Raises: ListenStoreException if unable to queue the deletion in the listens DB
        """
        query = """
            INSERT INTO listen_delete_metadata(user_id, listened_at, recording_msid) 
                 VALUES (:user_id, :listened_at, :recording_msid)
        """
        try:
            with listens_db.engine.begin() as connection:
                connection.execute(
                    sqlalchemy.text(query),
                    {"listened_at": listened_at, "user_id": user_id, "recording_msid": recording_msid}
                )
        except (psycopg2.OperationalError, sqlalchemy.exc.OperationalError) as e:
            self.log.error("Cannot delete listen for user: %s" % str(e))
            raise ListenStoreException("Cannot queue listen deletion in the listens database") from e


class ListenStoreException(Exception):
    pass
