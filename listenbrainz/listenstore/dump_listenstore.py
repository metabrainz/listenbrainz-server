import os
import shutil
import subprocess
import tarfile
import time
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd
import psycopg2
import psycopg2.sql
import pyarrow as pa
import pyarrow.parquet as pq
import sqlalchemy
import tempfile
import orjson
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz import DUMP_LICENSE_FILE_PATH
from listenbrainz.db import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.db import timescale
from listenbrainz.db.user import get_all_usernames
from listenbrainz.listen import Listen
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.timescale_listenstore import DATA_START_YEAR_IN_SECONDS
from listenbrainz.utils import create_path

# These values are defined to create spark parquet files that are at most 128MB in size.
# This compression ration allows us to roughly estimate how full we can make files before starting a new one
PARQUET_APPROX_COMPRESSION_RATIO = 0.25

# This is the approximate amount of data to write to a parquet file in order to meet the max size
PARQUET_TARGET_SIZE = 134217728 / PARQUET_APPROX_COMPRESSION_RATIO  # 128MB / compression ratio


SPARK_LISTENS_SCHEMA = pa.schema([
    pa.field("listened_at", pa.timestamp("ms"), False),
    pa.field("created", pa.timestamp("ms"), False),
    pa.field("user_id", pa.int64(), False),
    pa.field("recording_msid", pa.string(), False),
    pa.field("artist_name", pa.string(), False),
    pa.field("artist_credit_id", pa.int64(), True),
    pa.field("release_name", pa.string(), True),
    pa.field("release_mbid", pa.string(), True),
    pa.field("recording_name", pa.string(), False),
    pa.field("recording_mbid", pa.string(), True),
    pa.field("artist_credit_mbids", pa.list_(pa.string()), True),
])


class DumpListenStore:

    def __init__(self, app):
        self.log = app.logger
        self.dump_temp_dir_root = os.path.join("/code", "listenbrainz", "dumps")

    def get_listens_query_for_dump(self, start_time, end_time, max_created):
        """
            Get a query and its args dict to select a batch for listens for the full dump.
            Use listened_at timestamp, since not all listens have the created timestamp.
        """
        # filter on created timestamp in addition to listened_at as well to avoid duplicates
        # with incremental dumps in case of listens imported with past listened_at values
        # use max created timestamp instead of end_time because regardless of which start-end
        # range is being dumped the created limit should be the same and max desired.
        query = """SELECT extract(epoch from listened_at) as listened_at, user_id, created, recording_msid::TEXT, data
                      FROM listen
                     WHERE listened_at >= :start_time
                       AND listened_at <= :end_time
                       AND created <= :max_created
                  ORDER BY listened_at ASC"""
        args = {
            "start_time": start_time,
            "end_time": end_time,
            "max_created": max_created,
        }

        return query, args

    def get_incremental_listens_query(self, start_time, end_time):
        """
            Get a query for a batch of listens for an incremental listen dump.
            This uses the `created` column to fetch listens.
        """

        query = """SELECT extract(epoch from listened_at) as listened_at, user_id, created, recording_msid::TEXT, data
                      FROM listen
                     WHERE created > :start_ts
                       AND created <= :end_ts
                  ORDER BY created ASC"""

        args = {
            'start_ts': start_time,
            'end_ts': end_time,
        }
        return query, args

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

    def write_listens(self, temp_dir, tar_file, archive_name,
                      start_time_range, end_time_range, full_dump):
        """ Dump listens in the format for the ListenBrainz dump.

        Args:
            end_time_range (datetime): the range of time for the listens dump.
            temp_dir (str): the dir to use to write files before adding to archive
            full_dump (bool): the type of dump
        """
        user_id_map = get_all_usernames()
        max_created = end_time_range
        t0 = time.monotonic()
        listen_count = 0

        year = start_time_range.year
        month = start_time_range.month
        while True:
            start_time = datetime(year, month, 1, tzinfo=timezone.utc)
            start_time = max(start_time_range, start_time)
            if start_time > end_time_range:
                break

            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year += 1

            end_time = datetime(next_year, next_month, 1, tzinfo=timezone.utc)
            end_time = end_time - timedelta(seconds=1)
            if end_time > end_time_range:
                end_time = end_time_range

            filename = os.path.join(temp_dir, str(year), "%d.listens" % month)
            try:
                os.makedirs(os.path.join(temp_dir, str(year)))
            except FileExistsError:
                pass

            if full_dump:
                query, args = self.get_listens_query_for_dump(start_time, end_time, max_created)
            else:
                query, args = self.get_incremental_listens_query(start_time, end_time)

            rows_added = 0
            with timescale.engine.connect() as connection:
                curs = connection.execute(sqlalchemy.text(query), args)
                if curs.rowcount:
                    with open(filename, "w") as out_file:
                        while True:
                            result = curs.fetchone()
                            if not result:
                                break
                            # some listens have user id which is absent from user table
                            # ignore those listens for now
                            user_name = user_id_map.get(result.user_id)
                            if not user_name:
                                continue
                            listen = Listen.from_timescale(
                                listened_at=result.listened_at,
                                recording_msid=result.recording_msid,
                                user_id=result.user_id,
                                created=result.created,
                                track_metadata=result.data,
                                user_name=user_name
                            ).to_json()
                            out_file.write(orjson.dumps(listen).decode("utf-8") + "\n")
                            rows_added += 1
                    tar_file.add(filename, arcname=os.path.join(
                        archive_name, 'listens', str(year), f"{month}.listens"
                    ))

                    listen_count += rows_added
                    self.log.info("%d listens dumped for %s at %.2f listens/s", listen_count,
                                  start_time.strftime("%Y-%m-%d"),
                                  listen_count / (time.monotonic() - t0))

            month = next_month
            year = next_year

    def dump_listens(self, location, dump_id, start_time, end_time, dump_type,
                     threads=DUMP_DEFAULT_THREAD_COUNT):
        """ Dumps all listens in the ListenStore into a .tar.zst archive.

        Files are created with UUIDs as names. Each file can contain listens for a number of users.
        An index.json file is used to save which file contains the listens of which users.

        This creates an incremental dump if start_time is specified (with range start_time to end_time),
        otherwise it creates a full dump with all listens.

        Args:
            location: the directory where the listens dump archive should be created
            dump_id (int): the ID of the dump in the dump sequence
            start_time and end_time (datetime): the time range for which listens should be dumped
            dump_type: whether listens are dumped for a full or incremental dump
            threads (int): the number of threads to use for compression

        Returns:
            the path to the dump archive
        """
        full_dump = dump_type == "full"
        self.log.info('Beginning dump of listens from TimescaleDB...')
        archive_name = f'listenbrainz-listens-dump-{dump_id}-{end_time.strftime("%Y%m%d-%H%M%S")}'
        if full_dump:
            archive_name = '{}-full'.format(archive_name)
        else:
            archive_name = '{}-incremental'.format(archive_name)
        archive_path = os.path.join(location, f'{archive_name}.tar.zst')
        with open(archive_path, 'w') as archive:
            zstd_command = ['zstd', '--compress', f'-T{threads}', '-10']
            zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=zstd.stdin, mode='w|') as tar:
                temp_dir = os.path.join(self.dump_temp_dir_root, str(uuid.uuid4()))
                create_path(temp_dir)
                self.write_dump_metadata(
                    archive_name, start_time, end_time,
                    temp_dir, tar, full_dump
                )

                listens_path = os.path.join(temp_dir, 'listens')
                self.write_listens(
                    listens_path, tar, archive_name,
                    start_time, end_time, full_dump
                )

                # remove the temporary directory
                shutil.rmtree(temp_dir)

            zstd.stdin.close()

        zstd.wait()
        self.log.info('ListenBrainz listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path

    def write_parquet_files(self,
                            archive_dir,
                            temp_dir,
                            tar_file,
                            dump_type,
                            start_time: datetime,
                            end_time: datetime,
                            max_created: datetime,
                            parquet_file_id=0):
        """
            Carry out fetching listens from the DB, joining them to the MBID mapping table and
            then writing them to parquet files.

        Args:
            archive_dir: the directory where the listens dump archive should be created
            temp_dir: the directory where tmp files should be written
            tar_file: the tarfile object that the dumps are being written to
            dump_type: type of dump, full or incremental
            start_time: the start of the time range for which listens should be dumped
            end_time: the end of the time range for which listens should be dumped
            max_created: the max timestamp listens created beyond which should not be dumped
            parquet_file_id: the file id number to use for indexing parquet files

        Returns:
            the next parquet_file_id to use.

        """
        # the spark listens dump is sorted using this column. full dumps are sorted on
        # listened_at because so during loading listens in spark for stats calculation
        # we can load a subset of files. however, sorting on listened_at creates the
        # issue that the data imported today with listened_at in the past won't show up
        # in the stats until the next full dump. to solve this, we sort and dump incremental
        # listens using the created column. all incremental listens are always loaded by spark
        # , so we can get upto date stats sooner.
        if dump_type == "full":
            # filter on created timestamp in addition to listened_at as well to avoid duplicates
            # with incremental dumps in case of listens imported with past listened_at values
            # use max created timestamp instead of end_time because regardless of which start-end
            # range is being dumped the created limit should be the same and max desired.
            where_clause = psycopg2.sql.SQL("""
                    l.listened_at > %(start)s
                AND l.listened_at <= %(end)s
                AND l.created <= %(max_created)s
            """)
            order_by = psycopg2.sql.SQL("l.listened_at")
        else:  # incremental dump
            where_clause = psycopg2.sql.SQL("l.created > %(start)s AND l.created <= %(end)s")
            order_by = psycopg2.sql.SQL("l.created")
        args = {
            "start": start_time,
            "end": end_time,
            "max_created": max_created
        }

        query = psycopg2.sql.SQL("""
        -- can't use coalesce here because we want all listen data or all mapping data to be used for a given
        -- listen, coalesce mapping data with listen data can yield values from different sources for same listen.
        -- an alternative is to use to CASE, but need to put case for each column because SQL CASE doesn't allow
        -- setting multiple columns at once.
                WITH listen_with_mbid AS (
                     SELECT l.listened_at
                          , l.created::timestamp(3) with time zone AS created -- reduce timestamp resolution to ms
                          , l.user_id
                          , l.recording_msid
                          -- converting jsonb array to text array is non-trivial, so return a jsonb array not text
                          -- here and let psycopg2 adapt it to a python list which is what we want anyway
                          , data->'additional_info'->'artist_mbids' AS l_artist_credit_mbids
                          , data->>'artist_name' AS l_artist_name
                          , data->>'release_name' AS l_release_name
                          , data->'additional_info'->>'release_mbid' AS l_release_mbid
                          , data->>'track_name' AS l_recording_name
                          , data->'additional_info'->>'recording_mbid' AS l_recording_mbid
                          -- prefer to use user specified mapping, then mbid mapper's mapping, finally other user's specified mappings
                          , COALESCE(user_mm.recording_mbid, mm.recording_mbid, other_mm.recording_mbid) AS m_recording_mbid
                       FROM listen l
                  LEFT JOIN mbid_mapping mm
                         ON l.recording_msid = mm.recording_msid
                  LEFT JOIN mbid_manual_mapping user_mm
                         ON l.recording_msid = user_mm.recording_msid
                        AND user_mm.user_id = l.user_id 
                  LEFT JOIN mbid_manual_mapping_top other_mm
                         ON l.recording_msid = other_mm.recording_msid
                      WHERE {where_clause}
                )    SELECT l.listened_at
                          , l.created
                          , l.user_id
                          , l.recording_msid::TEXT
                          , l_artist_credit_mbids
                          , l_artist_name
                          , l_release_name
                          , l_release_mbid
                          , l_recording_name
                          , l_recording_mbid
                          , m_recording_mbid::TEXT
                          , (artist_data->'artist_credit_id')::INT AS artist_credit_id
                          , mbc.artist_mbids::TEXT[] AS m_artist_credit_mbids
                          , mbc.artist_data->>'name' AS m_artist_name
                          , mbc.release_mbid::TEXT AS m_release_mbid
                          , mbc.release_data->>'name' AS m_release_name
                          , mbc.recording_data->>'name' AS m_recording_name
                       FROM listen_with_mbid l
                  LEFT JOIN mapping.mb_metadata_cache mbc
                         ON l.m_recording_mbid = mbc.recording_mbid
                   ORDER BY {order_by}
        """).format(where_clause=where_clause, order_by=order_by)

        listen_count = 0
        current_listened_at = None
        conn = timescale.engine.raw_connection()
        with (conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs):
            curs.execute(query, args)
            while True:
                t0 = time.monotonic()
                written = 0
                approx_size = 0
                data = {
                    'listened_at': [],
                    'created': [],
                    'user_id': [],
                    'recording_msid': [],
                    'artist_name': [],
                    'artist_credit_id': [],
                    'release_name': [],
                    'release_mbid': [],
                    'recording_name': [],
                    'recording_mbid': [],
                    'artist_credit_mbids': []
                }
                while True:
                    result = curs.fetchone()
                    if not result:
                        break

                    # Either take the original listen metadata or the mapping metadata
                    if result["artist_credit_id"] is None:
                        data["artist_name"].append(result["l_artist_name"])
                        data["release_name"].append(result["l_release_name"])
                        data["recording_name"].append(result["l_recording_name"])
                        data["artist_credit_id"].append(None)
                        data["artist_credit_mbids"].append(result["l_artist_credit_mbids"])
                        data["release_mbid"].append(result["l_release_mbid"])
                        data["recording_mbid"].append(result["l_recording_mbid"])
                        approx_size += len(result["l_artist_name"]) + len(result["l_recording_name"]) \
                            + len(result["l_release_name"] or "0") + len(result["l_recording_mbid"] or "0") \
                            + len(result["l_release_mbid"] or "0") + len(str(result["l_artist_credit_mbids"] or 0))
                    else:
                        data["artist_name"].append(result["m_artist_name"])
                        data["release_name"].append(result["m_release_name"])
                        data["recording_name"].append(result["m_recording_name"])
                        data["artist_credit_id"].append(result["artist_credit_id"])
                        data["artist_credit_mbids"].append(result["m_artist_credit_mbids"])
                        data["release_mbid"].append(result["m_release_mbid"])
                        data["recording_mbid"].append(result["m_recording_mbid"])
                        approx_size += len(result["m_artist_name"]) + len(result["m_recording_name"]) \
                            + len(result["m_release_name"] or "0") + len(result["m_recording_mbid"] or "0") \
                            + len(result["m_release_mbid"] or "0") + len(str(result["m_artist_credit_mbids"] or 0)) \
                            + len(str(result["artist_credit_id"]))

                    current_listened_at = result["listened_at"]
                    data["listened_at"].append(current_listened_at)
                    data["created"].append(result["created"])
                    data["user_id"].append(result["user_id"])
                    data["recording_msid"].append(result["recording_msid"])
                    approx_size += len(str(result["listened_at"])) + len(str(result["created"])) \
                                   + len(str(result["user_id"])) + len(result["recording_msid"])

                    written += 1
                    listen_count += 1
                    if approx_size > PARQUET_TARGET_SIZE:
                        break

                if written == 0:
                    break

                filename = os.path.join(temp_dir, "%d.parquet" % parquet_file_id)

                # Create a pandas dataframe, then write that to a parquet files
                df = pd.DataFrame(data, dtype=object)
                table = pa.Table.from_pandas(df, schema=SPARK_LISTENS_SCHEMA, preserve_index=False)
                pq.write_table(table, filename, flavor="spark", compression="zstd")
                file_size = os.path.getsize(filename)
                tar_file.add(filename, arcname=os.path.join(archive_dir, "%d.parquet" % parquet_file_id))
                os.unlink(filename)
                parquet_file_id += 1

                self.log.info("%d listens dumped for %s at %.2f listens/s (%sMB)",
                              listen_count, current_listened_at.strftime("%Y-%m-%d"),
                              written / (time.monotonic() - t0),
                              str(round(file_size / (1024 * 1024), 3)))

        return parquet_file_id

    def dump_listens_for_spark(self, location,
                               dump_id: int,
                               dump_type: str,
                               start_time: datetime,
                               end_time: datetime):
        """ Dumps all listens in the ListenStore into spark parquet files in a .tar archive.

        Listens are dumped into files ideally no larger than 128MB, sorted from oldest to newest. Files
        are named #####.parguet with monotonically increasing integers starting with 0.

        This creates an incremental dump if start_time is specified (with range start_time to end_time),
        otherwise it creates a full dump with all listens.

        Args:
            location: the directory where the listens dump archive should be created
            dump_id: the ID of the dump in the dump sequence
            dump_type: type of dump, full or incremental
            start_time: the start of the time range for which listens should be dumped. defaults to
                utc 0 (meaning a full dump)
            end_time: the end of time range for which listens should be dumped. defaults to the current time

        Returns:
            the path to the dump archive
        """
        self.log.info('Beginning spark dump of listens from TimescaleDB...')
        full_dump = dump_type == "full"
        archive_name = 'listenbrainz-spark-dump-{dump_id}-{time}'.format(dump_id=dump_id,
                                                                         time=end_time.strftime('%Y%m%d-%H%M%S'))
        if full_dump:
            archive_name = f'{archive_name}-full'
        else:
            archive_name = f'{archive_name}-incremental'
        archive_path = os.path.join(location, f'{archive_name}.tar')

        max_created = end_time

        parquet_index = 0
        with tarfile.open(archive_path, "w") as tar:

            temp_dir = os.path.join(self.dump_temp_dir_root, str(uuid.uuid4()))
            create_path(temp_dir)
            self.write_dump_metadata(archive_name, start_time, end_time, temp_dir, tar, full_dump)

            for year in range(start_time.year, end_time.year + 1):
                if year == start_time.year:
                    start = start_time
                else:
                    start = datetime(year=year, day=1, month=1)
                if year == end_time.year:
                    end = end_time
                else:
                    end = datetime(year=year + 1, day=1, month=1)

                self.log.info(
                    "dump %s to %s" % (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")))

                # This try block is here in an effort to expose bugs that occur during testing
                # Without it sometimes test pass and sometimes they give totally unrelated errors.
                # Keeping this block should help with future testing...
                try:
                    parquet_index = self.write_parquet_files(archive_name, temp_dir, tar, dump_type,
                                                             start, end, max_created, parquet_index)
                except Exception as err:
                    self.log.exception("likely test failure: " + str(err))
                    raise

            shutil.rmtree(temp_dir)

        self.log.info('ListenBrainz spark listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path

    def cleanup_listen_delete_metadata(self):
        """ Cleanup listen delete metadata after spark full dump is complete """
        self.log.info("Cleaning up listen_delete_metadata")
        with timescale.engine.connect() as connection:
            connection.execute(text("DELETE FROM listen_delete_metadata WHERE status != 'pending'"))
            connection.execute(text("DELETE FROM deleted_user_listen_history"))
            connection.commit()
        self.log.info("Cleaning up listen_delete_metadata done!")
