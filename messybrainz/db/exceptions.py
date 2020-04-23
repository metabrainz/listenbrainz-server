class MessyBrainzException(Exception):
    """Base exception for this package."""
    pass

class NoDataFoundException(MessyBrainzException):
    """Should be used when no data has been found."""
    pass

class BadDataException(MessyBrainzException):
    """Should be used when incorrect data is being submitted."""
    pass

class ErrorAddingException(MessyBrainzException):
    """Should be used when incorrect data is being submitted."""
    pass
