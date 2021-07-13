from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, validator, constr
from listenbrainz.db.model.validators import check_rec_mbid_msid_is_valid_uuid, check_datetime_has_tzinfo
from messybrainz import load_recording_from_msid, load_recording_from_mbid

DAYS_UNTIL_UNPIN = 7  # default = unpin after one week
MAX_BLURB_CONTENT_LENGTH = 280  # maximum length of blurb content


class PinnedRecording(BaseModel):
    """Represents a pinned recording object.
    Args:
        user_id: the row id of the user in the DB
        row_id: the row id of the pinned_recording in the DB
        recording_mbid: the MusicBrainz ID of the recording
        blurb_content: (Optional) the custom text content of the pinned recording
        created: the datetime containing tzinfo representing when the pinned recording record was inserted into DB
        pinned_until: the datetime containing tzinfo representing when the pinned recording is set to expire/unpin

        Validates that pinned_until contains tzinfo() and is greater than created.
    """

    user_id: int
    user_name: Optional[str]
    row_id: int
    recording_msid: str
    recording_mbid: str = None
    blurb_content: constr(max_length=MAX_BLURB_CONTENT_LENGTH) = None
    created: datetime
    pinned_until: datetime
    track_metadata: dict = None

    _validate_recording_msid: classmethod = validator("recording_msid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)

    _validate_recording_mbid: classmethod = validator("recording_mbid", allow_reuse=True)(check_rec_mbid_msid_is_valid_uuid)

    _validate_created_tzinfo: classmethod = validator("created", always=True, allow_reuse=True)(check_datetime_has_tzinfo)

    _validate_pin_until_tzinfo: classmethod = validator("pinned_until", always=True, allow_reuse=True)(check_datetime_has_tzinfo)

    # also must validate that pinned_until datetime greater than created
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

    row_id: int = None
    created: datetime = None
    pinned_until: datetime = None

    # set default datetime for created
    @validator("created", pre=True, always=True)
    def set_created_to_default_now(cls, created):
        return datetime.now(timezone.utc)

    # set default datetime for pinned_until if argument wasn't provided
    @validator("pinned_until", pre=True, always=True)
    def set_pinned_until_to_default(cls, pin_until, values):
        return pin_until or values["created"] + timedelta(days=DAYS_UNTIL_UNPIN)


def fetch_track_metadata_for_pin(pin: PinnedRecording) -> PinnedRecording:
    """ Fetches track_metadata (track_name, artist_name, release_name...) for a given PinnedRecording.

        Args:
            pin (PinnedRecording): the PinnedRecording to fetch track_metadata for.
        Returns:
            The given pin with track_metadata.
    """
    if pin.recording_mbid:
        metadata = load_recording_from_mbid(pin.recording_mbid)['payload']
    else:
        metadata = load_recording_from_msid(pin.recording_msid)['payload']

    pin.track_metadata = {"track_name": metadata["title"], "artist_name": metadata["artist"]}
    return pin
