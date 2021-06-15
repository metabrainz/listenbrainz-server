from datetime import datetime, timedelta
from pydantic import BaseModel, validator
from listenbrainz.db.model.utils import check_rec_mbid_msid_is_valid_uuid, check_datetime_has_tzinfo_or_set_now

DAYS_UNTIL_UNPIN = 7  # default = unpin after one week


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

    _is_recording_mbid_valid: classmethod = validator("recording_mbid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)

    _is_created_valid: classmethod = validator("created", always=True, allow_reuse=True)(check_datetime_has_tzinfo_or_set_now)

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
                return values["created"] + timedelta(days=DAYS_UNTIL_UNPIN)  # set default value
            else:
                raise ValueError("Cannot set default pinned_until until created is valid.")
