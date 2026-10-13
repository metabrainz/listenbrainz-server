from datetime import datetime, timezone


def to_utc(value: datetime) -> datetime:
    """Return ``value`` as an aware UTC datetime; a naive value is taken to be UTC already."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
