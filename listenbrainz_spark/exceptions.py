class SparkException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SQLException(SparkException):
    """ Failed to execute an SQL query
    """
    pass

class FileNotSavedException(SparkException):
    def __init__(self, message, file_path):
        self.error_msg = 'File could not be saved to {}\n{}'.format(file_path, message)
        super(FileNotSavedException, self).__init__(self.error_msg)

