from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import field_validator, model_validator, Field

from data.model.validators import check_datetime_has_tzinfo
from listenbrainz.db.msid_mbid_mapping import MsidMbidModel

#: Default number of days after which a pinned recording expires (gets unpinned).
DAYS_UNTIL_UNPIN = 7
MAX_BLURB_CONTENT_LENGTH = 280  # maximum length of blurb content


class PinnedRecording(MsidMbidModel):
    """Represents a pinned recording object.
    Args:
        user_id: the row id of the user in the DB
        user_name: (Optional) the name of the user associated with the user_id
        row_id: the row id of the pinned_recording in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: the datetime containing tzinfo representing when the pinned recording record was inserted into DB
        pinned_until: the datetime containing tzinfo representing when the pinned recording is set to expire/unpin

        Validates that pinned_until contains tzinfo() and is greater than created.
    """

    user_id: int = Field(ge=0)
    user_name: Optional[str] = None
    row_id: int = Field(ge=0)
    blurb_content: Optional[str] = Field(default=None, max_length=MAX_BLURB_CONTENT_LENGTH)
    created: datetime
    pinned_until: datetime

    @field_validator("created", "pinned_until", mode="before")
    @classmethod
    def validate_tzinfo(cls, v):
        return check_datetime_has_tzinfo(v)

    @model_validator(mode="after")
    def check_pin_until_greater_than_created(self):
        if self.pinned_until <= self.created:
            raise ValueError("Pinned_until of returned PinnedRecording must be greater than created.")
        return self

    def to_api(self):
        pin = self.model_dump()
        pin["created"] = int(pin["created"].timestamp())
        pin["pinned_until"] = int(pin["pinned_until"].timestamp())
        del pin["user_id"]
        if pin["user_name"] is None:
            del pin["user_name"]
        return pin


class WritablePinnedRecording(PinnedRecording):
    """Represents a pinned recording object to pin/submit to the DB.
       This model does not require a row_id, initializes created to now(), and initializes pinned_until to now() + one week.

    Args:
        user_id: the row id of the user in the DB
        row_id: (Optional) the row id of the pinned_recording in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: (Optional) the datetime containing tzinfo representing when the pinned recording record was inserted into DB
        pinned_until: (Optional) the datetime containing tzinfo representing when the pinned recording is set to expire/unpin

    """

    row_id: Optional[int] = Field(default=None, ge=0)
    created: Optional[datetime] = None
    pinned_until: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, data):
        if isinstance(data, dict):
            if not data.get("created"):
                data["created"] = datetime.now(timezone.utc)
            if not data.get("pinned_until"):
                data["pinned_until"] = data["created"] + timedelta(days=DAYS_UNTIL_UNPIN)
        return data
