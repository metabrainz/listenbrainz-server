from typing import Union

from pydantic import constr, NonNegativeInt

from data.model.common_stat_spark import StatMessage, UserStatRecords
from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord

# Order of the records in union is important and should be from more specific to less specific
# For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
EntityRecord = Union[RecordingRecord, ReleaseGroupRecord, ReleaseRecord, ArtistRecord]


class UserEntityRecords(UserStatRecords[EntityRecord]):
    count: NonNegativeInt


class UserEntityStatMessage(StatMessage[UserEntityRecords]):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording
