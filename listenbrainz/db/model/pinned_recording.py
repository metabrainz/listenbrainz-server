from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, validator
from listenbrainz.db.model.utils import check_rec_mbid_msid_is_valid_uuid, check_datetime_has_tzinfo

DAYS_UNTIL_UNPIN = 7  # default = unpin after one week


class PinnedRecording(BaseModel):
    """Represents a pinned recording object.
    Args:
        user_id: the row id of the user in the DB
        row_id: the row id of the pinned_recording in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: the timestamp when the pinned recording record was inserted into DB
        pinned_until: the timestamp when the pinned recording is set to expire/unpin

        Validates that pinned_until contains tzinfo() and is greater than created.
    """

    user_id: int
    user_name: Optional[str]
    row_id: int
    recording_mbid: str
    blurb_content: str = None
    created: datetime
    pinned_until: datetime

    _validate_recording_mbid: classmethod = validator("recording_mbid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)

    _validate_created_tzinfo: classmethod = validator("created", always=True, allow_reuse=True)(check_datetime_has_tzinfo)

    # need to validate tzinfo and greater than created
    _validate_pin_until_tzinfo: classmethod = validator("pinned_until", always=True, allow_reuse=True)(check_datetime_has_tzinfo)

    @validator("pinned_until", always=True)
    def check_pin_until_greater_than_created(cls, pin_until, values):
        try:
            if pin_until <= values["created"]:
                raise ValueError
            return pin_until
        except (ValueError, AttributeError):
            raise ValueError(
                """Pinned_until of returned PinnedRecording must be greater than created.
                        See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
            )


class PinnedRecordingSubmit(BaseModel):
    """Represents a pinned recording object to pin/submit to the DB. Created is initialized to now().

    Args:
        user_id: the row id of the user in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        pinned_until: (Optional) the timestamp when the pinned recording is set to expire/unpin

        Pinned_until is set to created + _daysUntilUnpin (7 days) by default.
        If pinned_until is provided, the model validates that it contains tzinfo() and is greater than created.

    """

    user_id: int
    recording_mbid: str
    blurb_content: str = None
    created: datetime = None
    pinned_until: datetime = None

    _validate_recording_mbid: classmethod = validator("recording_mbid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)

    @validator("created", pre=True, always=True)
    def set_created_now(cls, created):
        return datetime.now(timezone.utc)

    @validator("pinned_until", always=True)
    def check_valid_pinned_until_or_set(cls, pin_until, values):
        if pin_until:
            try:
                if pin_until.tzinfo is None or pin_until.tzinfo.utcoffset(pin_until) is None or pin_until < values["created"]:
                    raise ValueError
                return pin_until
            except (ValueError, AttributeError):
                raise ValueError(
                    """Pinned until must be a valid datetime, contain tzinfo, and be greater than now().
                            See https://pydantic-docs.helpmanual.io/usage/types/#datetime-types for acceptable formats."""
                )
        else:
            return values["created"] + timedelta(days=DAYS_UNTIL_UNPIN)  # set default value
