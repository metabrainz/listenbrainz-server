"""
Functions for exporting and importing AcousticBrainz data in various formats.

There are two types of data dumps:
1. Full dumps (high/low level information about all recordings in JSON format
or raw information from all tables in TSV format).
2. Incremental dumps (similar to the first one, but some dumped tables don't
include information from the previous dumps).
"""
from __future__ import print_function
from collections import defaultdict
from datetime import datetime
from db import create_cursor, commit
import utils.path
import db
import subprocess
import tempfile
import logging
import tarfile
import shutil
import os

DUMP_CHUNK_SIZE = 1000
DUMP_LICENSE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                      "licenses", "COPYING-PublicDomain")

# Importing of old dumps will fail if you change
# definition of columns below.
_TABLES = {
    "lowlevel": (
        "id",
        "mbid",
        "build_sha1",
        "lossless",
        "data",
        "submitted",
        "data_sha256",
    ),
    "highlevel": (
        "id",
        "mbid",
        "build_sha1",
        "data",
        "submitted",
    ),
    "highlevel_json": (
        "id",
        "data",
        "data_sha256",
    ),
    "statistics": (
        "name",
        "value",
        "collected",
    ),
    "incremental_dumps": (
        "id",
        "created",
    ),
}


def dump_db(location, threads=None, incremental=False, dump_id=None):
    """Create database dump in a specified location.

    Args:
        location: Directory where archive will be created.
        threads: Maximal number of threads to run during compression.
        incremental: False if resulting data dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created dump.
    """
    utils.path.create_path(location)
    time_now = datetime.today()

    if incremental:
        dump_id, start_t, end_t = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-dump-incr-%s" % dump_id
    else:
        start_t, end_t = None, None  # full
        archive_name = "acousticbrainz-dump-%s" % time_now.strftime("%Y%m%d-%H%M%S")

    archive_path = os.path.join(location, archive_name + ".tar.xz")
    with open(archive_path, "w") as archive:

        pxz_command = ["pxz", "--compress"]
        if threads is not None:
            pxz_command.append("-T %s" % threads)
        pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

        # Creating the archive
        with tarfile.open(fileobj=pxz.stdin, mode="w|") as tar:
            # TODO(roman): Get rid of temporary directories and write directly to tar file if that's possible.
            temp_dir = tempfile.mkdtemp()

            # Adding metadata
            schema_seq_path = os.path.join(temp_dir, "SCHEMA_SEQUENCE")
            with open(schema_seq_path, "w") as f:
                f.write(str(db.SCHEMA_VERSION))
            tar.add(schema_seq_path,
                    arcname=os.path.join(archive_name, "SCHEMA_SEQUENCE"))
            timestamp_path = os.path.join(temp_dir, "TIMESTAMP")
            with open(timestamp_path, "w") as f:
                f.write(time_now.isoformat(" "))
            tar.add(timestamp_path,
                    arcname=os.path.join(archive_name, "TIMESTAMP"))
            tar.add(DUMP_LICENSE_FILE_PATH,
                    arcname=os.path.join(archive_name, "COPYING"))

            archive_tables_dir = os.path.join(temp_dir, "abdump", "abdump")
            utils.path.create_path(archive_tables_dir)
            _copy_tables(archive_tables_dir, start_t, end_t)
            tar.add(archive_tables_dir, arcname=os.path.join(archive_name, "abdump"))

            shutil.rmtree(temp_dir)  # Cleanup

        pxz.stdin.close()

    return archive_path


def _copy_tables(location, start_time=None, end_time=None):
    """Copies all tables into separate files within a specified location (directory).

    ou can also define time frame that will be used during data selection.
    Files in a specified directory will only contain rows that have timestamps
    within specified time frame. We assume that each table contains some sort
    of timestamp that can be used as a reference.
    """
    def generate_where(row_name, start_t=start_time, end_t=end_time):
        """This function generates SQL WHERE clause that can be used to select
        rows only within specified time frame using `row_name` as a reference.
        """
        if start_t or end_t:
            start_cond = "%s > '%s'" % (row_name, str(start_t)) if start_t else ""
            end_cond = "%s <= '%s'" % (row_name, str(end_t)) if end_t else ""
            if start_t and end_t:
                return "WHERE %s AND %s" % (start_cond, end_cond)
            else:
                return "WHERE %s%s" % (start_cond, end_cond)
        else:
            return ""

    with create_cursor() as cursor:

        # lowlevel
        with open(os.path.join(location, "lowlevel"), "w") as f:
            logging.info(" - Copying table lowlevel...")
            cursor.copy_to(f, "(SELECT %s FROM lowlevel %s)" %
                           (", ".join(_TABLES["lowlevel"]), generate_where("submitted")))

        # highlevel
        with open(os.path.join(location, "highlevel"), "w") as f:
            logging.info(" - Copying table highlevel...")
            cursor.copy_to(f, "(SELECT %s FROM highlevel %s)" %
                           (", ".join(_TABLES["highlevel"]), generate_where("submitted")))

        # highlevel_json
        with open(os.path.join(location, "highlevel_json"), "w") as f:
            logging.info(" - Copying table highlevel_json...")
            query = "SELECT %s FROM highlevel_json WHERE id IN (SELECT data FROM highlevel %s)" \
                    % (", ".join(_TABLES["highlevel_json"]), generate_where("submitted"))
            cursor.copy_to(f, "(%s)" % query)

        # statistics
        with open(os.path.join(location, "statistics"), "w") as f:
            logging.info(" - Copying table statistics...")
            cursor.copy_to(f, "(SELECT %s FROM statistics %s)" %
                           (", ".join(_TABLES["statistics"]), generate_where("collected")))

        # incremental_dumps
        with open(os.path.join(location, "incremental_dumps"), "w") as f:
            logging.info(" - Copying table incremental_dumps...")
            cursor.copy_to(f, "(SELECT %s FROM incremental_dumps %s)" %
                           (", ".join(_TABLES["incremental_dumps"]), generate_where("created")))


def import_db_dump(archive_path):
    """Import data from .tar.xz archive into the database."""
    pxz_command = ["pxz", "--decompress", "--stdout", archive_path]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

    table_names = _TABLES.keys()

    with create_cursor() as cursor:

        with tarfile.open(fileobj=pxz.stdout, mode="r|") as tar:
            for member in tar:
                file_name = member.name.split("/")[-1]

                if file_name == "SCHEMA_SEQUENCE":
                    # Verifying schema version
                    schema_seq = int(tar.extractfile(member).read().strip())
                    if schema_seq != db.SCHEMA_VERSION:
                        raise Exception("Incorrect schema version! Expected: %d, got: %d."
                                        "Please, get the latest version of the dump."
                                        % (db.SCHEMA_VERSION, schema_seq))
                    else:
                        logging.info("Schema version verified.")

                else:
                    if file_name in table_names:
                        logging.info(" - Importing data into %s table..." % file_name)
                        cursor.copy_from(tar.extractfile(member), '"%s"' % file_name,
                                         columns=_TABLES[file_name])

    commit()
    pxz.stdout.close()


def dump_lowlevel_json(location, incremental=False, dump_id=None):
    """Create JSON dump with low level data.

    Args:
        location: Directory where archive will be created.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created low level JSON dump.
    """
    utils.path.create_path(location)

    if incremental:
        dump_id, start_time, end_time = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-lowlevel-json-incr-%s" % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = "acousticbrainz-lowlevel-json-%s" % \
                       datetime.today().strftime("%Y%m%d")

    archive_path = os.path.join(location, archive_name + ".tar.bz2")
    with tarfile.open(archive_path, "w:bz2") as tar:

        with create_cursor() as cursor:

            mbid_occurences = defaultdict(int)

            # Need to count how many duplicate MBIDs are there before start_time
            if start_time:
                cursor.execute("""
                    SELECT mbid, count(id)
                    FROM lowlevel
                    WHERE submitted <= %s
                    GROUP BY mbid
                    """, (start_time,))
                counts = cursor.fetchall()
                for mbid, count in counts:
                    mbid_occurences[mbid] = count

            if start_time or end_time:
                start_cond = "submitted > '%s'" % str(start_time) if start_time else ""
                end_cond = "submitted <= '%s'" % str(end_time) if end_time else ""
                if start_time and end_time:
                    where = "WHERE %s AND %s" % (start_cond, end_cond)
                else:
                    where = "WHERE %s%s" % (start_cond, end_cond)
            else:
                where = ""
            cursor.execute("SELECT id FROM lowlevel ll %s ORDER BY mbid" % where)

            with create_cursor() as cursor_inner:
                temp_dir = tempfile.mkdtemp()

                dumped_count = 0

                while True:
                    id_list = cursor.fetchmany(size=DUMP_CHUNK_SIZE)
                    if not id_list:
                        break
                    id_list = tuple([i[0] for i in id_list])

                    cursor_inner.execute("""SELECT mbid, data::text
                                            FROM lowlevel
                                            WHERE id IN %s
                                            ORDER BY mbid""", (id_list,))
                    while True:
                        row = cursor_inner.fetchone()
                        if not row:
                            break
                        mbid, json = row

                        json_filename = mbid + "-%d.json" % mbid_occurences[mbid]
                        dump_tempfile = os.path.join(temp_dir, json_filename)
                        with open(dump_tempfile, "w") as f:
                            f.write(json)
                        tar.add(dump_tempfile, arcname=os.path.join(
                            archive_name, "lowlevel", mbid[0:1], mbid[0:2], json_filename))
                        os.unlink(dump_tempfile)

                        mbid_occurences[mbid] += 1
                        dumped_count += 1

        # Copying legal text
        tar.add(DUMP_LICENSE_FILE_PATH,
                arcname=os.path.join(archive_name, "COPYING"))

        shutil.rmtree(temp_dir)  # Cleanup

        logging.info("Dumped %s recordings." % dumped_count)

    return archive_path


def dump_highlevel_json(location, incremental=False, dump_id=None):
    """Create JSON dump with high-level data.

    Args:
        location: Directory where archive will be created.
        incremental: False if resulting JSON dump should be complete, False if
            it needs to be incremental.
        dump_id: If you need to reproduce previously created incremental dump,
            its identifier (integer) can be specified there.

    Returns:
        Path to created high-level JSON dump.
    """
    utils.path.create_path(location)

    if incremental:
        dump_id, start_time, end_time = prepare_incremental_dump(dump_id)
        archive_name = "acousticbrainz-highlevel-json-incr-%s" % dump_id
    else:
        start_time, end_time = None, None  # full
        archive_name = "acousticbrainz-highlevel-json-%s" % \
                       datetime.today().strftime("%Y%m%d")

    archive_path = os.path.join(location, archive_name + ".tar.bz2")
    with tarfile.open(archive_path, "w:bz2") as tar:

        with create_cursor() as cursor:
            mbid_occurences = defaultdict(int)

            # Need to count how many duplicate MBIDs are there before start_time
            if start_time:
                cursor.execute("""
                    SELECT mbid, count(id)
                    FROM highlevel
                    WHERE submitted <= %s
                    GROUP BY mbid
                    """, (start_time,))
                counts = cursor.fetchall()
                for mbid, count in counts:
                    mbid_occurences[mbid] = count

            if start_time or end_time:
                start_cond = "hl.submitted > '%s'" % str(start_time) if start_time else ""
                end_cond = "hl.submitted <= '%s'" % str(end_time) if end_time else ""
                if start_time and end_time:
                    where = "AND %s AND %s" % (start_cond, end_cond)
                else:
                    where = "AND %s%s" % (start_cond, end_cond)
            else:
                where = ""
            cursor.execute("""SELECT hl.id
                              FROM highlevel hl, highlevel_json hlj
                              WHERE hl.data = hlj.id %s
                              ORDER BY mbid""" % where)

            with create_cursor() as cursor_inner:
                temp_dir = tempfile.mkdtemp()

                dumped_count = 0

                while True:
                    id_list = cursor.fetchmany(size=DUMP_CHUNK_SIZE)
                    if not id_list:
                        break
                    id_list = tuple([i[0] for i in id_list])

                    cursor_inner.execute("""SELECT mbid, hlj.data::text
                                            FROM highlevel hl, highlevel_json hlj
                                            WHERE hl.data = hlj.id AND hl.id IN %s
                                            ORDER BY mbid""", (id_list, ))
                    while True:
                        row = cursor_inner.fetchone()
                        if not row:
                            break
                        mbid, json = row

                        json_filename = mbid + "-%d.json" % mbid_occurences[mbid]
                        dump_tempfile = os.path.join(temp_dir, json_filename)
                        with open(dump_tempfile, "w") as f:
                            f.write(json)
                        tar.add(dump_tempfile, arcname=os.path.join(
                            archive_name, "highlevel", mbid[0:1], mbid[0:2], json_filename))
                        os.unlink(dump_tempfile)

                        mbid_occurences[mbid] += 1
                        dumped_count += 1

        # Copying legal text
        tar.add(DUMP_LICENSE_FILE_PATH,
                arcname=os.path.join(archive_name, "COPYING"))

        shutil.rmtree(temp_dir)  # Cleanup

        logging.info("Dumped %s recordings." % dumped_count)

    return archive_path


def list_incremental_dumps():
    """Get information about all created incremental dumps.

    Returns:
        List of (id, created) pairs ordered by dump identifier, or None if
        there are no incremental dumps yet.
    """
    with create_cursor() as cursor:
        cursor.execute("SELECT id, created FROM incremental_dumps ORDER BY id DESC")
        return cursor.fetchall()


def prepare_incremental_dump(dump_id=None):
    if dump_id:  # getting existing
        existing_dumps = list_incremental_dumps()
        start_t, end_t = None, None
        if existing_dumps:
            for i, dump_info in enumerate(existing_dumps):
                if dump_info[0] == dump_id:
                    end_t = dump_info[1]
                    # Getting info about the dump before that specified
                    start_t = existing_dumps[i+1][1] if i+1 < len(existing_dumps) else None
                    break
        if not start_t and not end_t:
            raise Exception("Cannot find incremental dump with a specified ID."
                            " Please check if it exists or create a new one.")

    else:  # creating new
        start_t = _get_incremental_dump_timestamp()
        if start_t and not _any_new_data(start_t):
            raise NoNewData("No new data since the last incremental dump!")
        dump_id, end_t = _create_new_inc_dump_record()

    return dump_id, start_t, end_t


def _any_new_data(from_time):
    """Checks if there's any new data since specified time in tables that
    support incremental dumps.

    Returns:
        True if there is new data in one of tables that support incremental
        dumps, False if there is no new data there.
    """
    with create_cursor() as cursor:
        cursor.execute("SELECT count(*) FROM lowlevel WHERE submitted > %s", (from_time,))
        lowlevel_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM highlevel WHERE submitted > %s", (from_time,))
        highlevel_count = cursor.fetchone()[0]
    return lowlevel_count > 0 or highlevel_count > 0


def _create_new_inc_dump_record():
    """Creates new record for incremental dump and returns its ID and creation time."""
    with create_cursor() as cursor:
        cursor.execute("INSERT INTO incremental_dumps (created) VALUES (now()) RETURNING id, created")
        commit()
        row = cursor.fetchone()
    logging.info("Created new incremental dump record (ID: %s)." % row[0])
    return row


def _get_incremental_dump_timestamp(dump_id=None):
    with create_cursor() as cursor:
        if dump_id:
            cursor.execute("SELECT created FROM incremental_dumps WHERE id = %s", (dump_id,))
        else:
            cursor.execute("SELECT created FROM incremental_dumps ORDER BY id DESC")
        row = cursor.fetchone()
    return row[0] if row else None


class NoNewData(Exception):
    pass
