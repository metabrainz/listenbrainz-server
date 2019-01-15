import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import hdfs

import listenbrainz_spark
import listenbrainz_spark.config as config

from datetime import datetime
from hdfs.util import HdfsError
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.schema import convert_listen_to_row, listen_schema, convert_to_spark_json
import pyspark.sql.functions as sql_functions

FORCE = True

def _is_listens_file(filename):
    """ Check if passed filename is a file which contains listens

    Args:
        filename (str): the name of the file

    Returns:
        bool: True if the file contains listens, False otherwise
    """
    return filename.endswith('.listens')


def _process_listens_file(filename, tmp_dir):
    """ Process a file containing listens from the ListenBrainz dump and add listens to
    appropriate dataframes.
    """
    start_time = time.time()
    unwritten_listens = {}
    with open(filename) as f:
        for line in f:
            listen = json.loads(line)
            timestamp = datetime.utcfromtimestamp(listen['listened_at'])
            year = timestamp.year
            month = timestamp.month
            json_data = convert_to_spark_json(listen)

            if year not in unwritten_listens:
                unwritten_listens[year] = {}
            if month not in unwritten_listens[year]:
                unwritten_listens[year][month] = []
            unwritten_listens[year][month].append(json_data)

    write_listens(unwritten_listens, tmp_dir)
    print("File processed in %.2f seconds!" % (time.time() - start_time))


def write_listens(unwritten_listens, tmp_dir):
    for year in unwritten_listens:
        for month in unwritten_listens[year]:
            if year < LAST_FM_FOUNDING_YEAR:
                filename = os.path.join(tmp_dir, 'json', 'invalid.json')
            else:
                filename = os.path.join(tmp_dir, 'json', str(year), '{}.json'.format(str(month)))
            with open(filename, 'a') as f:
                for listen in unwritten_listens[year][month]:
                    f.write(json.dumps(listen))
                    f.write("\n")
            unwritten_listens[year][month] = []


def copy_to_hdfs(archive, threads=8):
    """ Create Spark Dataframes from a listens dump and save it to HDFS.

    Args:
        archive (str): the path to the listens dump
        threads (int): the number of threads to use for decompression of the archive
    """
    tmp_dump_dir = tempfile.mkdtemp()
    pxz_command = ['pxz', '--decompress', '--stdout', archive, '-T{}'.format(threads)]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)
    destination_path = os.path.join('/', 'data', 'listenbrainz')
    if FORCE:
        print('Removing data directory if present...')
        hdfs_connection.client.delete(destination_path, recursive=True)
        print('Done!')

    file_count = 0
    total_time = 0.0
    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        for member in tar:
            if member.isfile() and _is_listens_file(member.name) and file_count <= 1:
                print('Loading %s...' % member.name)
                t = time.time()
                tar.extract(member)
                listenbrainz_spark.context.addFile(member.name)
                _process_listens_file(member.name, tmp_dump_dir)
                os.remove(member.name)
                file_count += 1
                time_taken = time.time() - t
                print("Done! Processed %d files. Current file done in %.2f sec" % (file_count, time_taken))
                total_time += time_taken
                average_time = total_time / file_count
                print("Total time: %.2f, average time: %.2f" % (total_time, average_time))

    print("Writing dataframes...")
    total_time = 0
    file_count = 0
    for year in range(LAST_FM_FOUNDING_YEAR, datetime.today().year + 1):
        for month_index in range(12):
            t = time.time()
            print("Writing dataframe for %d/%d..." % (month_index + 1, year))
            src_path = os.path.join(tmp_dump_dir, 'json', str(year), '{}.json'.format(str(month)))
            df = listenbrainz_spark.session.read.json(src_path, schema=listen_schema)
            dest_path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, str(year), str(month_index + 1) + '.parquet')
            df.write.format('parquet').save(dest_path)
            os.remove(src_path)
            time_taken = time.time() - t
            print("Done in %.2f seconds!" % (time_taken))
            total_time += time_taken
            average_time = total_time / file_count
            print("Total time: %.2f, average time: %.2f" % (total_time, average_time))
    print("Dataframes written!")

    print("Writing dataframe for invalid listens to HDFS: %s" % path)
    src_path = os.path.join(tmp_dump_dir, 'json', 'invalid.json')
    t = time.time()
    invalid_df = listenbrainz_spark.session.read.json(src_path, schema=listen_schema)
    dest_path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, 'invalid.parquet')
    invalid_df.write.format('parquet').save(dest_path)
    print("Done in %.2f sec!" % (time.time() - t))

    print("Deleting temporary directories...")
    shutil.rmtree(tmp_dump_dir)


def main(app_name, archive):
    listenbrainz_spark.init_spark_session(app_name)
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    print('Copying extracted dump to HDFS...')
    copy_to_hdfs(archive)
    print('Done!')
