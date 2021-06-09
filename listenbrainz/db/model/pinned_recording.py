import uuid

from datetime import date, datetime, timezone, timedelta
from pydantic import BaseModel, validator, Field


class PinnedRecording(BaseModel):
    """Represents a pinned recording object.
    Args:
        user_id: the row id of the user in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: (Optional) the timestamp when the pinned recording record was inserted into DB
        pinned_until: (Optional) the timestamp when the pinned recording is set to expire/unpin

        Created is set to now() by default. Pinned_until is set to created + 7 days by default.
        If arguments are provided but either is invalid, the object will not be created.
    """

    user_id: int
    recording_mbid: str
    blurb_content: str = None
    created: datetime = None
    pinned_until: datetime = None

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
            try:  # validate datetime contains tzinfo
                assert (
                    created.tzinfo is not None
                    and created.tzinfo.utcoffset(created) is not None  # v.tzinfo throws AttributeError if invalid datetime
                ), "Created must contain tzinfo."
                return created
            except (AttributeError, ValueError):
                raise ValueError("Created must be a valid datetime and contain tzinfo.")
        else:
            return datetime.now(timezone.utc)  # set default value

    @validator("pinned_until", always=True)
    def check_valid_pinned_until_or_set(cls, pin_until, values):
        try:
            if pin_until:  # validate if argument provided
                try:
                    assert (
                        pin_until.tzinfo is not None and pin_until.tzinfo.utcoffset(pin_until) is not None
                    ), "Pinned_until must contain tzinfo."
                    assert pin_until > values["created"], "Pinned until must be greater than created."
                    return pin_until
                except (AttributeError, ValueError):  # v.tzinfo throws AttributeError if invalid datetime
                    raise ValueError("Pinned_until must be a valid datetime and contain tzinfo.")
            else:
                return values["created"] + timedelta(days=7)  # set default value
        except (KeyError):  # values["created"] throws KeyError if created was not valid
            raise ValueError("Cannot set default pinned_until until created is valid.")
