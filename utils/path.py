import errno
import os


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to create directory structure %s. Error: %s" %
                            (path, exception))
