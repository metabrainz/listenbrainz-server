import os
import subprocess
import tarfile
import tempfile
import hdfs

import listenbrainz_spark.config as config

from hdfs.util import HdfsError
from listenbrainz_spark import spark, sc

FORCE = True

def copy_to_hdfs(archive):
    pxz_command = ['pxz', '--decompress', '--stdout', archive, '-T4']
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)
    hdfs_client = hdfs.InsecureClient(config.HDFS_NAMENODE_URI, user='root')
    destination_path = os.path.join('/', 'data', 'listenbrainz')
    if FORCE:
        print('Removing data directory if present...')
        hdfs_client.delete(destination_path, recursive=True)
        print('Done!')

    print('Creating remote directory...')
    hdfs_client.makedirs(destination_path)
    print('Done!')

    print('Uploading...')
    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        for member in tar:
            if member.isfile():
                tar.extract(member)
                print("Uploading %s to %s..." % (os.path.join(destination_path, member.name), member.name))
                hdfs_client.upload(os.path.join(destination_path, member.name), member.name)
                os.remove(member.name)
    print("Done!")


def main(archive):
    print('Copying extracted dump to HDFS...')
    copy_to_hdfs(archive)
    print('Done!')
