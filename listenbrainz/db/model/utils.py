import uuid
from datetime import datetime, timezone


def check_rec_mbid_msid_is_valid_uuid(rec_id: str):
    """Validates that a recording MBID or MSID is a valid UUID. Otherwise, raises a ValueError.

    Args:
        rec_id: the recording MBID/MSID to validate.

    Returns:
        The validated recording MBID/MSID as a string.
    """
    try:
        rec_id = uuid.UUID(rec_id)
        return str(rec_id)
    except (AttributeError, ValueError):
        raise ValueError("Recording MBID/MSID must be a valid UUID.")


def check_datetime_has_tzinfo_or_set_now(date_time: datetime = None):
    """Validates that the provided datetime object contains tzinfo. Otherwise, raises a ValueError.

    Args:
        date_time: the datetime object to validate.

    Returns:
        The provided datetime object containing tzinfo if it was valid.
        If no object was provided, returns now() as a datetime containing tzinfo.
    """
    if date_time:  # validate if argument provided
        try:  # validate that datetime contains tzinfo
            if date_time.tzinfo is None or date_time.tzinfo.utcoffset(date_time) is None:
                raise ValueError
            return date_time
        except (AttributeError, ValueError):
            raise ValueError(
                """Datetime provided must be a valid datetime and contain tzinfo.
                       See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
            )
    else:
        return datetime.now(timezone.utc)  # set default value
