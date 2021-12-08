from datetime import datetime, timedelta, timezone
from typing import Optional, List

from pydantic import validator, constr, NonNegativeInt

from data.model.validators import check_datetime_has_tzinfo
from listenbrainz.db.mapping import MsidMbidModel, load_recordings_from_mapping
from listenbrainz.messybrainz import load_recordings_from_msids

DAYS_UNTIL_UNPIN = 7  # default = unpin after one week
MAX_BLURB_CONTENT_LENGTH = 280  # maximum length of blurb content


class PinnedRecording(MsidMbidModel):
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

    user_id: NonNegativeInt
    user_name: Optional[str]
    row_id: NonNegativeInt
    blurb_content: constr(max_length=MAX_BLURB_CONTENT_LENGTH) = None
    created: datetime
    pinned_until: datetime
    track_metadata: dict = None

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

    row_id: NonNegativeInt = None
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


def fetch_track_metadata_for_pins(pins: List[PinnedRecording]) -> List[PinnedRecording]:
    """ Fetches track_metadata for every object in a list of PinnedRecordings.

        Args:
            pins (List of PinnedRecordings): the PinnedRecordings to fetch track_metadata for.
        Returns:
            The given list of PinnedRecording objects with updated track_metadata.
    """
    msid_pin_map, mbid_pin_map = {}, {}
    for pin in pins:
        if pin.recording_mbid:
            mbid_pin_map[pin.recording_mbid] = pin
        else:
            msid_pin_map[pin.recording_msid] = pin

    msid_metadatas = load_recordings_from_msids(msid_pin_map.keys())
    for msid, pin in msid_pin_map.items():
        metadata = msid_metadatas[msid]
        pin.track_metadata = {
            "track_name": metadata["payload"]["title"],
            "artist_name": metadata["payload"]["artist"],
            "additional_info": {
                "recording_msid": msid
            }
        }

    mapping_mbid_metadata, mapping_msid_metadata = load_recordings_from_mapping(mbid_pin_map.keys(), msid_pin_map.keys())

    for mbid, pin in mbid_pin_map.keys():
        metadata = mapping_mbid_metadata[mbid]
        pin.track_metadata = {
            "track_name": metadata["title"],
            "artist_name": metadata["artist"],
            "release_name": metadata["release"],
            "additional_info": {
                "recording_msid": metadata["recording_msid"],
                "recording_mbid": metadata["recording_mbid"],
                "release_mbid": metadata["release_mbid"],
                "artist_mbids": metadata["artist_mbids"]
            }
        }

    for msid, pin in msid_pin_map.keys():
        if msid in mapping_msid_metadata:
            continue

        metadata = mapping_msid_metadata[msid]
        pin.track_metadata = {
            "track_name": metadata["title"],
            "artist_name": metadata["artist"],
            "release_name": metadata["release"],
            "additional_info": {
                "recording_msid": metadata["recording_msid"],
                "recording_mbid": metadata["recording_mbid"],
                "release_mbid": metadata["release_mbid"],
                "artist_mbids": metadata["artist_mbids"]
            }
        }

    return pins
