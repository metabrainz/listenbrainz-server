import uuid
from datetime import datetime


def check_valid_uuid(param: str):
    """Validates that a UUID is valid or None. Otherwise, raises a ValueError.

    Args:
        param: the UUID to validate.

    Returns:
        The validated recording UUID as a string.
    """
    if param is None:
        return None
    try:
        param = uuid.UUID(param)
        return str(param)
    except (AttributeError, ValueError):
        raise ValueError(f"'{param}' must be a valid UUID.")


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
