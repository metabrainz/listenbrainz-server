import uuid

from datetime import date, datetime, timezone, timedelta
from pydantic import BaseModel, validator, Field


class PinnedRecording(BaseModel):
    """Represents a pinned recording object.
    Args:
        user_id: the row id of the user in the DB
        row_id: (Optional) the row id of the pinned_recording in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: (Optional) the timestamp when the pinned recording record was inserted into DB
        pinned_until: (Optional) the timestamp when the pinned recording is set to expire/unpin

        Created is set to now() by default. Pinned_until is set to created + _daysUntilUnpin (7 days) by default.
        If arguments are provided but either is invalid, the object will not be created.
    """

    user_id: int
    row_id: int = None
    recording_mbid: str
    blurb_content: str = None
    created: datetime = None
    pinned_until: datetime = None

    _daysUntilUnpin = 7  # default = unpin after one week

    @validator("recording_mbid")
    def check_recording_msid_is_valid_uuid(cls, rec_mbid):
        try:
            rec_mbid = uuid.UUID(rec_mbid)
            return str(rec_mbid)
        except (AttributeError, ValueError):
            raise ValueError("Recording MSID must be a valid UUID.")

    @validator("created", always=True)
    def check_valid_created_or_set(cls, created):
        if created:  # validate if argument provided
            try:  # validate that datetime contains tzinfo
                if created.tzinfo is None or created.tzinfo.utcoffset(created) is None:
                    raise ValueError
                return created
            except (AttributeError, ValueError):  # created.tzinfo throws AttributeError if invalid datetime
                raise ValueError(
                    """Created must be a valid datetime and contain tzinfo.
                       See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
                )
        else:
            return datetime.now(timezone.utc)  # set default value

    @validator("pinned_until", always=True)
    def check_valid_pinned_until_or_set(cls, pin_until, values):
        if pin_until:
            try:
                if pin_until.tzinfo is None or pin_until.tzinfo.utcoffset(pin_until) is None or pin_until < values["created"]:
                    raise ValueError
                return pin_until
            except (ValueError, AttributeError):
                raise ValueError(
                    """Pinned until must be a valid datetime, contain tzinfo, and be greater than created.
                            See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
                )
        else:
            if "created" in values:
                return values["created"] + timedelta(days=cls._daysUntilUnpin)  # set default value
            else:
                raise ValueError("Cannot set default pinned_until until created is valid.")
