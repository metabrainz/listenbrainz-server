from datetime import datetime
from typing import List, Union

import pydantic

from data.model.common_stat import StatRange, StatApi
from data.model.user_artist_stat import UserArtistRecord
from data.model.user_recording_stat import UserRecordingRecord
from data.model.user_release_stat import UserReleaseRecord

# Order of the records in union is important and should be from more specific to less specific
# For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
UserEntityStatRecord = Union[UserRecordingRecord, UserReleaseRecord, UserArtistRecord]


class UserEntityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    musicbrainz_id: str
    type: str
    entity: str  # The entity for which stats are calculated, i.e artist, release or recording
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: int
    to_ts: int
    data: List[UserEntityStatRecord]
    count: int


# we need this so that we can call json(exclude_none=True) when inserting in the db
# not sure if this is necessary but preserving the old behaviour for now. json.dumps
# does not have an exclude_none option.
class UserEntityRecordList(pydantic.BaseModel):
    __root__: List[UserEntityStatRecord]
