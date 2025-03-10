import logging
from pathlib import Path

from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.exceptions import HDFSDirectoryNotDeletedException

logger = logging.getLogger(__name__)


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
    return hdfs_connection.client.status(path, strict=False)


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


def move(hdfs_src_path: str, hdfs_dest_path: str):
    """ Move a file or folder in HDFS """
    # Delete existing destination directory if any
    if path_exists(hdfs_dest_path):
        logger.info(f'Removing {hdfs_dest_path} from HDFS...')
        delete_dir(hdfs_dest_path, recursive=True)
        logger.info('Done!')

    logger.info(f"Moving the processed files from {hdfs_src_path} to {hdfs_dest_path}")

    # Check if parent directory exists, if not create a directory
    dest_path_parent = str(Path(hdfs_dest_path).parent)
    if not path_exists(dest_path_parent):
        create_dir(dest_path_parent)

    rename(hdfs_src_path, hdfs_dest_path)
    logger.info(f"Done!")