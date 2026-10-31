import os
import time
from datetime import datetime

import orjson
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import text

from listenbrainz.db import listens as listens_db
from listenbrainz.db.user import get_all_usernames
from listenbrainz.dumps import DUMP_DEFAULT_THREAD_COUNT
from listenbrainz.dumps.exporter import zstd_dump, uncompressed_dump
from listenbrainz.listen import Listen
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION

# Listens are selected for dumps in pages of this many listens, each in its own query and transaction, so
# that neither the memory used nor the transactions grow with the number of listens of a user or a time range.
DUMP_PAGE_SIZE = 100_000

# Full dumps page through the partitions of the listen table in the order of their (user_id, listened_at)
# index. Incremental dumps page through listens in the order they were created.
LISTEN_DUMP_COLUMNS = "extract(epoch from l.listened_at) AS listened_at, l.user_id, l.created, l.recording_msid::TEXT, l.data"
# reduce the created timestamp resolution to ms for spark
SPARK_PAGE_COLUMNS = "l.listened_at, l.created::timestamp(3) with time zone AS created, l.user_id, l.recording_msid, l.data"


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
        self.page_size = DUMP_PAGE_SIZE

    def iter_dump_files(self, select, wrap, start_time, end_time, full_dump):
        """ Yield one page iterator per output file: each partition for full dumps, one for incremental.

        select specifies columns from the listen table aliased l; wrap adds any mapping joins to the
        page query. Full dumps also filter on created to leave later imports for incremental dumps.
        """
        args = {"start_time": start_time, "end_time": end_time}
        if full_dump:
            where = "l.listened_at >= :start_time AND l.listened_at <= :end_time AND l.created <= :end_time"
            partitions = listens_db.get_listen_partitions()
        else:
            where = "l.created > :start_time AND l.created <= :end_time"
            partitions = ["listen"]

        for partition in partitions:
            def page_query(after, _partition=partition):
                if full_dump:
                    query, page_args = listens_db.partition_page_query(_partition, select, where, after)
                else:
                    query, page_args = listens_db.created_page_query(select, where, after)
                return wrap(query), page_args
            yield listens_db.iter_listen_pages(self.page_size, page_query, args)

    def get_dump_metadata(self, start_time: datetime, end_time: datetime, full_dump):
        """ Get metadata to write into the dump archive.

        Args:
            start_time: the start time of the dump
            end_time: the end time of the dump
            full_dump (bool): flag to specify whether the archive is a full dump or an incremental dump
        """
        metadata: dict[str, int | str | datetime] = {
            "SCHEMA_SEQUENCE": LISTENS_DUMP_SCHEMA_VERSION,
        }
        if full_dump:
            metadata["TIMESTAMP"] = end_time
        else:
            metadata["START_TIMESTAMP"] = start_time
            metadata["END_TIMESTAMP"] = end_time
        return metadata

    def write_listens(self, temp_dir, tar_file, archive_name,
                      start_time_range, end_time_range, full_dump):
        """ Dump listens in the format for the ListenBrainz dump.

        A full dump writes the listens of each partition of the listen table to its own numbered file, sorted
        by user and then listened_at, newest first, so all listens of a user are in one file. An incremental
        dump writes all listens to one file, in the order they were created.

        Args:
            end_time_range (datetime): the range of time for the listens dump.
            temp_dir (str): the dir to use to write files before adding to archive
            full_dump (bool): the type of dump
        """
        user_id_map = get_all_usernames()
        t0 = time.monotonic()
        listen_count = 0
        os.makedirs(temp_dir, exist_ok=True)

        def write_file(file_id, pages):
            """ Write the listens in pages to a numbered file and add it to the archive if there are any """
            nonlocal listen_count
            filename = os.path.join(temp_dir, f"{file_id}.listens")
            rows_added = 0
            with open(filename, "w") as out_file:
                for page in pages:
                    for result in page:
                        # some listens have user id which is absent from user table
                        # ignore those listens for now
                        user_name = user_id_map.get(result["user_id"])
                        if not user_name:
                            continue
                        listen = Listen.from_timescale(
                            listened_at=result["listened_at"],
                            recording_msid=result["recording_msid"],
                            user_id=result["user_id"],
                            created=result["created"],
                            track_metadata=result["data"],
                            user_name=user_name
                        ).to_json()
                        out_file.write(orjson.dumps(listen).decode("utf-8") + "\n")
                        rows_added += 1
                    listen_count += len(page)
                    self.log.info("%d listens dumped at %.2f listens/s", listen_count,
                                  listen_count / (time.monotonic() - t0))
            if rows_added:
                tar_file.add(filename, arcname=os.path.join(archive_name, 'listens', f"{file_id}.listens"))
            os.unlink(filename)
            return rows_added > 0

        file_id = 0
        for pages in self.iter_dump_files(
            LISTEN_DUMP_COLUMNS, lambda query: query, start_time_range, end_time_range, full_dump
        ):
            if write_file(file_id, pages):
                file_id += 1

    def dump_listens(self, location, dump_id, start_time, end_time, dump_type,
                     threads=DUMP_DEFAULT_THREAD_COUNT, temp_location=None):
        """ Dumps all listens in the ListenStore into a .tar.zst archive.

        Full dumps write one numbered file per nonempty partition. Incremental dumps write one file
        containing listens created in (start_time, end_time]. dump_type selects full or incremental.

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
        self.log.info('Beginning dump of listens from the listens DB...')
        archive_name = f'listenbrainz-listens-dump-{dump_id}-{end_time.strftime("%Y%m%d-%H%M%S")}'
        if full_dump:
            archive_name = '{}-full'.format(archive_name)
        else:
            archive_name = '{}-incremental'.format(archive_name)

        metadata = self.get_dump_metadata(start_time, end_time, full_dump)
        with zstd_dump(location, archive_name, metadata, threads, temp_location=temp_location) as (zstd, tar, temp_dir, archive_path):
            listens_path = os.path.join(temp_dir, 'listens')
            self.write_listens(
                listens_path, tar, archive_name,
                start_time, end_time, full_dump
            )
        self.log.info('ListenBrainz listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path

    @staticmethod
    def spark_dump_query(page_query: str, by_created: bool = False) -> str:
        """ Wrap a page query selecting SPARK_PAGE_COLUMNS into the query to select the page's listens
            with their mapping for the spark dump, in the same order. by_created is whether the page query
            pages by created. """
        key_columns = "l.key_user_id, l.key_listened_at, l.key_recording_msid"
        order_by = "ORDER BY l.key_user_id, l.key_listened_at DESC, l.key_recording_msid"
        if by_created:
            key_columns += ", l.key_created"
            order_by = "ORDER BY l.key_created, l.key_user_id, l.key_listened_at, l.key_recording_msid"
        return f"""
                WITH page AS (
                    {page_query}
                ), listen_with_mbid AS (
                     SELECT l.*
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
                       FROM page l
                  LEFT JOIN mapping.mbid_mapping mm
                         ON l.recording_msid = mm.recording_msid
                  LEFT JOIN mapping.mbid_manual_mapping user_mm
                         ON l.recording_msid = user_mm.recording_msid
                        AND user_mm.user_id = l.user_id
                  LEFT JOIN mapping.mbid_manual_mapping_top other_mm
                         ON l.recording_msid = other_mm.recording_msid
                )    SELECT l.listened_at
                          , l.created
                          , l.user_id
                          , l.recording_msid::TEXT
                          , {key_columns}
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
                          {order_by}
        """

    def write_parquet_file(self, archive_dir, temp_dir, tar_file, file_id, pages):
        """ Stream pages into one numbered parquet file, adding it to the archive if nonempty. """
        filename = os.path.join(temp_dir, f"{file_id}.parquet")
        listen_count = 0
        t0 = time.monotonic()
        with pq.ParquetWriter(filename, SPARK_LISTENS_SCHEMA, flavor="spark", compression="zstd") as writer:
            for page in pages:
                data = {column: [] for column in SPARK_LISTENS_SCHEMA.names}
                for result in page:
                    # Use one metadata source for the whole listen, never a mixture of both.
                    prefix = "l_" if result["artist_credit_id"] is None else "m_"
                    for column in ("artist_name", "release_name", "recording_name", "artist_credit_mbids",
                                   "release_mbid", "recording_mbid"):
                        data[column].append(result[prefix + column])
                    for column in ("artist_credit_id", "listened_at", "created", "user_id", "recording_msid"):
                        data[column].append(result[column])
                writer.write_table(pa.Table.from_pydict(data, schema=SPARK_LISTENS_SCHEMA))
                listen_count += len(page)
                self.log.info("%d listens dumped at %.2f listens/s", listen_count,
                              listen_count / (time.monotonic() - t0))

        if listen_count:
            tar_file.add(filename, arcname=os.path.join(archive_dir, f"{file_id}.parquet"))
        os.unlink(filename)
        return listen_count > 0

    def dump_listens_for_spark(
        self, location, dump_id: int, dump_type: str,
        start_time: datetime, end_time: datetime,
        temp_location: str = None,
    ):
        """ Dumps all listens in the ListenStore into spark parquet files in a .tar archive.

        Full dumps write one numbered parquet file per nonempty partition, in user and newest-listen
        order. Incremental dumps write one file in created order for (start_time, end_time]. Each query
        page is written as a row group, keeping memory bounded regardless of file size.

        Args:
            location: the directory where the listens dump archive should be created
            dump_id: the ID of the dump in the dump sequence
            dump_type: type of dump, full or incremental
            start_time: the start of the time range for which listens should be dumped
            end_time: the end of the time range for which listens should be dumped

        Returns:
            the path to the dump archive
        """
        self.log.info('Beginning spark dump of listens from the listens DB...')
        full_dump = dump_type == "full"
        archive_name = 'listenbrainz-spark-dump-{dump_id}-{time}'.format(dump_id=dump_id,
                                                                         time=end_time.strftime('%Y%m%d-%H%M%S'))
        if full_dump:
            archive_name = f'{archive_name}-full'
        else:
            archive_name = f'{archive_name}-incremental'

        metadata = self.get_dump_metadata(start_time, end_time, full_dump)
        with uncompressed_dump(location, archive_name, metadata, temp_location=temp_location) as (tar, temp_dir, archive_path):

            file_id = 0
            for pages in self.iter_dump_files(
                SPARK_PAGE_COLUMNS, lambda query: self.spark_dump_query(query, by_created=not full_dump),
                start_time, end_time, full_dump
            ):
                if self.write_parquet_file(archive_name, temp_dir, tar, file_id, pages):
                    file_id += 1

        self.log.info('ListenBrainz spark listen dump done!')
        self.log.info('Dump present at %s!', archive_path)
        return archive_path

    def cleanup_listen_delete_metadata(self):
        """Clean up deletion records in the listens DB after a Spark full dump."""
        self.log.info("Cleaning up listen_delete_metadata")
        with listens_db.engine.begin() as connection:
            # Invalid requests matched no listen and need no retry, so clean them up
            # together with completed requests. Pending requests must still be processed.
            connection.execute(text("DELETE FROM listen_delete_metadata WHERE status != 'pending'"))
            connection.execute(text("DELETE FROM deleted_user_listen_history"))
        self.log.info("Cleaning up listen_delete_metadata done!")
