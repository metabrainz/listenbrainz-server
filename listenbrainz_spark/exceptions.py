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
        self.error_msg = 'DataFrame with following schema not appended: \n{}\n{}'.format(schema, message)
        super(DataFrameNotAppendedException, self).__init__(self.error_msg)

class DataFrameNotCreatedException(SparkException):
    """ Failed to create a new dataframe.
    """
    def __init__(self, message, row):
        self.error_msg = 'Cannot create dataframe for following row object: \n{}\n{}'.format(row, message)
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
        self.error_msg = 'File could not be fetched from {}\n{}'.format(file_path, message)
        super(FileNotFetchedException, self).__init__(self.error_msg)

class FileNotSavedException(SparkException):
    """ Failed to save a file to secondary storage.
    """
    def __init__(self, message, file_path):
        self.error_msg = 'File could not be saved to {}\n{}'.format(file_path, message)
        super(FileNotSavedException, self).__init__(self.error_msg)

class HDFSDirectoryNotDeletedException(HDFSException):
    """ Failed to delete an HDFS directory.
    """
    def __init__(self, message, file_path):
        self.error_msg = 'Directory with the following path could not be deleted: {}\n{}'.format(file_path, message)
        super(HDFSDirectoryNotDeletedException, self).__init__(self.error_msg)

class PathNotFoundException(SparkException):
    """ Failed to find a given path in secondary storage.
    """
    def __init__(self, message, path):
        self.error_msg = 'Path not found: {}\n{}'.format(path, message)
        super(PathNotFoundException, self).__init__(self.error_msg)

class SQLException(SparkException):
    """ Failed to execute an SQL query
    """
    pass

class SparkSessionNotInitializedException(SparkException):
    """ Failed to initialze Spark session.
    """
    def __init__(self, message, app_name):
        self.error_msg = 'Session {} not initialized\n{}'.format(app_name, message)
        super(SparkSessionNotInitializedException, self).__init__(self.error_msg)

class ViewNotRegisteredException(SparkException):
    """ Failed to register dataframe.
    """
    def __init__(self, message, table_name):
        self.error_msg = 'Dataframe not registered {}\n{}'.format(table_name, message)
        super(ViewNotRegisteredException, self).__init__(self.error_msg)



