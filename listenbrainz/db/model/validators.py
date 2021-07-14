import uuid
from datetime import datetime, timezone


def check_valid_uuid(param: str):
    """Validates that a UUID is valid. Otherwise, raises a ValueError.

    * Validating constr(min_length=1) accepts valid UUID's only, while
      validating Optional[str] accepts valid UUID's, None, and ''.

    Args:
        id: the UUID to validate.

    Returns:
        The validated recording UUID as a string.
    """
    if param is None:
        return None
    if param == '':
        return ''
    try:
        param = uuid.UUID(param)
        return str(param)
    except (AttributeError, ValueError):
        raise ValueError("'{}' must be a valid UUID.".format(param))


def check_datetime_has_tzinfo(date_time: datetime):
    """Validates that the provided datetime object contains tzinfo. Otherwise, raises a ValueError.

    Args:
        date_time: the datetime object to validate.

    Returns:
        The provided datetime object containing tzinfo if it was valid.
    """
    try:  # validate that datetime contains tzinfo
        if date_time.tzinfo is None or date_time.tzinfo.utcoffset(date_time) is None:
            raise ValueError
        return date_time
    except (AttributeError, ValueError):  # timestamp.tzinfo throws AttributeError if invalid datetime
        raise ValueError(
            """Datetime provided must be a valid datetime and contain tzinfo.
                    See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
        )
