import logging
import os

from hdfs.util import HdfsError

from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.exceptions import (HDFSDirectoryNotDeletedException,
                                           PathNotFoundException)

logger = logging.getLogger(__name__)


# A typical listen is of the form:
# {
#   "artist_mbids": [],
#   "artist_name": "Cake",
#   "listened_at": "2005-02-28T20:39:08Z",
#   "recording_msid": "c559b2f8-41ff-4b55-ab3c-0b57d9b85d11",
#   "recording_mbid": "1750f8ca-410e-4bdc-bf90-b0146cb5ee35",
#   "release_mbid": "",
#   "release_name": null,
#   "tags": [],
#   "track_name": "Tougher Than It Is"
#   "user_id": 5,
# }
# All the keys in the dict are column/field names in a Spark dataframe.


def create_dir(path):
    """ Creates a directory in HDFS.
        Args:
            path (string): Path of the directory to be created.
        Note: >> Caller is responsibe for initializing HDFS connection.
              >> The function does not throw an error if the directory path already exists.
    """
    hdfs_connection.client.makedirs(path)


def delete_dir(path, recursive=False):
    """ Deletes a directory recursively from HDFS.
        Args:
            path (string): Path of the directory to be deleted.
        Note: >> Caller is responsible for initializing HDFS connection.
              >> Raises HdfsError if trying to delete a non-empty directory.
                 For non-empty directory set recursive to 'True'.
    """
    deleted = hdfs_connection.client.delete(path, recursive=recursive)
    if not deleted:
        raise HDFSDirectoryNotDeletedException('', path)


def path_exists(path):
    """ Checks if the path exists in HDFS. The function returns False if the path
        does not exist otherwise returns True.
        Args:
            path (string): Path to check status for.
        Note: Caller is responsible for initializing HDFS connection.
    """
    path_found = hdfs_connection.client.status(path, strict=False)
    if path_found:
        return True
    return False


def hdfs_walk(path, depth=0):
    """ Depth-first walk of HDFS filesystem.
        Args:
            path (str): Path to start DFS.
            depth (int): Maximum depth to explore files/folders. 0 for no limit.
        Returns:
            walk: a generator yeilding tuples (path, dirs, files).
    """
    try:
        walk = hdfs_connection.client.walk(hdfs_path=path, depth=depth)
        return walk
    except HdfsError as err:
        raise PathNotFoundException(str(err), path)


def upload_to_HDFS(hdfs_path, local_path):
    """ Upload local file to HDFS.
        Args:
            hdfs_path (str): HDFS path to upload local file.
            local_path (str): Local path of file to be uploaded.
    """
    hdfs_connection.client.upload(hdfs_path=hdfs_path, local_path=local_path)


def rename(hdfs_src_path: str, hdfs_dst_path: str):
    """ Move a file or folder in HDFS
        Args:
            hdfs_src_path – Source path.
            hdfs_dst_path – Destination path. If the path already exists and is a directory, the source will be moved into it.
    """
    hdfs_connection.client.rename(hdfs_src_path, hdfs_dst_path)


def copy(hdfs_src_path: str, hdfs_dst_path: str, overwrite: bool = False):
    """ Copy a file or folder in HDFS
        Args:
            hdfs_src_path – Source path.
            hdfs_dst_path – Destination path. If the path already exists and is a directory, the source will be copied into it.
            overwrite - Wether to overwrite the path if it already exists.
    """
    walk = hdfs_walk(hdfs_src_path)

    for (root, dirs, files) in walk:
        for _file in files:
            src_file_path = os.path.join(root, _file)
            dst_file_path = os.path.join(hdfs_dst_path, os.path.relpath(src_file_path, hdfs_src_path))
            with hdfs_connection.client.read(src_file_path) as reader:
                with hdfs_connection.client.write(dst_file_path, overwrite=overwrite) as writer:
                    writer.write(reader.read())
