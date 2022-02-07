from typing import List, Union

from pydantic import BaseModel, NonNegativeInt, constr

from data.model.user_artist_stat import UserArtistRecord
from data.model.user_recording_stat import UserRecordingRecord
from data.model.user_release_stat import UserReleaseRecord

# Order of the records in union is important and should be from more specific to less specific
# For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
UserEntityRecord = Union[UserRecordingRecord, UserReleaseRecord, UserArtistRecord]


class MultipleUserEntityRecords(BaseModel):
    user_id: NonNegativeInt
    count: NonNegativeInt
    data: List[UserEntityRecord]


class UserEntityStatMessage(BaseModel):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    type: constr(min_length=1)
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    data: List[MultipleUserEntityRecords]
