class SparkException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class DataFrameNotAppendedException(SparkException):
    """ Failed to append a dataframe to existing dataframe in HDFS or
        failed to write a new dataframe to HDFS.
    """
    def __init__(self, message, schema):
        self.error_msg = (
            f'DataFrame with following schema not appended: \n{schema}\n{message}'
        )
        super(DataFrameNotAppendedException, self).__init__(self.error_msg)

class DataFrameNotCreatedException(SparkException):
    """ Failed to create a new dataframe.
    """
    def __init__(self, message, row):
        self.error_msg = (
            f'Cannot create dataframe for following row object: \n{row}\n{message}'
        )
        super(DataFrameNotCreatedException, self).__init__(self.error_msg)

class HDFSException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class FileNotFetchedException(SparkException):
    """ Failed to fetch a file from secondary storage.
    """
    def __init__(self, message, file_path):
        self.error_msg = f'File could not be fetched from {file_path}\n{message}'
        super(FileNotFetchedException, self).__init__(self.error_msg)

class FileNotSavedException(SparkException):
    """ Failed to save a file to secondary storage.
    """
    def __init__(self, message, file_path):
        self.error_msg = f'File could not be saved to {file_path}\n{message}'
        super(FileNotSavedException, self).__init__(self.error_msg)

class HDFSDirectoryNotDeletedException(HDFSException):
    """ Failed to delete an HDFS directory.
    """
    def __init__(self, message, file_path):
        self.error_msg = f'Directory with the following path could not be deleted: {file_path}\n{message}'
        super(HDFSDirectoryNotDeletedException, self).__init__(self.error_msg)

class PathNotFoundException(SparkException):
    """ Failed to find a given path in secondary storage.
    """
    def __init__(self, message, path):
        self.error_msg = f'Path not found: {path}\n{message}'
        super(PathNotFoundException, self).__init__(self.error_msg)

class SQLException(SparkException):
    """ Failed to execute an SQL query
    """
    pass

class SparkSessionNotInitializedException(SparkException):
    """ Failed to initialze Spark session.
    """
    def __init__(self, message, app_name):
        self.error_msg = f'Session {app_name} not initialized\n{message}'
        super(SparkSessionNotInitializedException, self).__init__(self.error_msg)

class ViewNotRegisteredException(SparkException):
    """ Failed to register dataframe.
    """
    def __init__(self, message, table_name):
        self.error_msg = f'Dataframe not registered {table_name}\n{message}'
        super(ViewNotRegisteredException, self).__init__(self.error_msg)

class DumpNotFoundException(SparkException):
    """ Failed to find data dump on FTP.
    """
    def __init__(self, message):
        super(DumpNotFoundException, self).__init__(message)


class DumpInvalidException(SparkException):
    """ The given dump is invalid, i.e the SHA256 checksum
        doesn't match or is not present
    """

    def __init__(self, message):
        super(DumpInvalidException, self).__init__(message)


class RecommendationsNotGeneratedException(SparkException):
    """ No recommendations generated for the given user.
    """
    def __init__(self, message):
        super(RecommendationsNotGeneratedException, self).__init__(message)


class RatingOutOfRangeException(SparkException):
    """ CF generated rating is out of range i.e. rating > 1 or rating < -1
    """
    def __init__(self, message):
        super(RatingOutOfRangeException, self).__init__(message)


class TopArtistNotFetchedException(SparkException):
    """ Top artists for user(s) not fetched.
    """
    def __init__(self, message):
        super(TopArtistNotFetchedException, self).__init__(message)


class SimilarArtistNotFetchedException(SparkException):
    """ Similar artists for user(s) not fetched.
    """
    def __init__(self, message):
        super(SimilarArtistNotFetchedException, self).__init__(message)

class EmptyDataframeExcpetion(SparkException):
    """ Dataframe is empty.
    """
    def __init__(self, message):
        super(EmptyDataframeExcpetion, self).__init__(message)
