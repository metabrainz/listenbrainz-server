from typing import List, Union

import pydantic

from data.model.user_artist_stat import UserArtistRecord
from data.model.user_recording_stat import UserRecordingRecord
from data.model.user_release_stat import UserReleaseRecord


class UserEntityStatMessage(pydantic.BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    musicbrainz_id: str
    type: str
    entity: str  # The entity for which stats are calculated, i.e artist, release or recording
    stats_range: str  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: int
    to_ts: int
    # Order of the records in union is important and should be from more specific to less specific
    # For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
    data: List[Union[UserRecordingRecord, UserReleaseRecord, UserArtistRecord]]
    count: int
