from datetime import datetime, timedelta, timezone
from typing import Optional, List

import sqlalchemy
from pydantic import BaseModel, validator, constr, NonNegativeInt

from listenbrainz.db import timescale
from data.model.validators import check_valid_uuid, check_datetime_has_tzinfo
from listenbrainz.messybrainz import load_recordings_from_msids

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

    user_id: NonNegativeInt
    user_name: Optional[str]
    row_id: NonNegativeInt
    recording_msid: constr(min_length=1)
    recording_mbid: Optional[str]
    blurb_content: constr(max_length=MAX_BLURB_CONTENT_LENGTH) = None
    created: datetime
    pinned_until: datetime
    track_metadata: dict = None

    _validate_recording_msid: classmethod = validator("recording_msid", "recording_mbid", allow_reuse=True)(check_valid_uuid)

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
    fetch_msids = [pin.recording_msid for pin in pins]  # retrieves list of msid's to fetch with
    msid_metadatas = load_recordings_from_msids(fetch_msids)
    # we can zip the pins and metadata because load_recordings_from_msids
    # returns the metadata in same order of the msid list passed to it
    for pin, metadata in zip(pins, msid_metadatas):
        pin.track_metadata = {
            "track_name": metadata["payload"]["title"],
            "artist_name": metadata["payload"]["artist"],
            "additional_info": {
                "artist_msid": metadata["ids"]["artist_msid"],
                "recording_msid": pin.recording_msid
            }
        }

    # find pins that have a mbid and use mapped data to overwrite msid data
    mbid_pins = [pin for pin in pins if pin.recording_mbid]

    if mbid_pins:
        query = """SELECT artist_credit_name AS artist, recording_name AS title, release_name AS release,
                          recording_mbid::TEXT, release_mbid::TEXT, artist_mbids::TEXT[]
                     FROM mbid_mapping_metadata
                    WHERE recording_mbid IN :mbids
                 ORDER BY recording_mbid"""
        # retrieves list of mbid's to fetch with
        mbids = tuple([pin.recording_mbid for pin in mbid_pins])
        with timescale.engine.connect() as connection:
            mbid_metadatas = connection.execute(sqlalchemy.text(query), mbids=mbids)

            # we can zip the pins and metadata because the query returns
            # the metadata in same order of the mbid list passed to it
            for pin, metadata in zip(mbid_pins, mbid_metadatas):
                pin.track_metadata.update({
                    "track_name": metadata["title"],
                    "artist_name": metadata["artist"],
                    "release_name": metadata["release"]
                })

                pin.track_metadata["additional_info"].update({
                    "recording_mbid": metadata["recording_mbid"],
                    "release_mbid": metadata["release_mbid"],
                    "artist_mbids": metadata["artist_mbids"]
                })

    return pins
