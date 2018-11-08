import os
import subprocess
import tempfile
import hdfs

import listenbrainz_spark.config as config

from hdfs.util import HdfsError
from listenbrainz_spark import spark, sc

FORCE = True

def extract(archive):
    directory = tempfile.mkdtemp()
    command = ['tar', '-xvf', archive, '-C', directory]
    try:
        x = subprocess.check_output(command)
        print('Extracted archive to %s!' % directory)
        return directory
    except subprocess.CalledProcessError as e:
        print('Error while extracting: %s' % str(e))
        print(e.output)
        raise


def copy_to_hdfs(directory):
    hdfs_client = hdfs.Client(config.HDFS_NAMENODE_URI)
    destination_path = os.path.join('/', 'data', 'listenbrainz')
    print('Creating remote directory...')
    if FORCE:
        hdfs_client.delete(destination_path, recursive=True)
    hdfs_client.makedirs(destination_path)
    print('Done!')

    print('Uploading...')
    for root, dirs, files in os.walk(directory):
        for directory in dirs:
            if 'listenbrainz-listens-dump' in directory:
                hdfs_client.upload(destination_path, os.path.join(root, directory))
                print('Upload done!')
                return


def main(archive):
    print('Extracting the archive...')
    extracted_dir = extract(archive)
    print('Done! Extracted to %s' % extracted_dir)

    print('Copying extracted dump to HDFS...')
    copy_to_hdfs(extracted_dir)
    print('Done!')
