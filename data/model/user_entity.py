from typing import Union

from pydantic import constr

from data.model.common_stat_spark import StatMessage, MultipleUserStatRecords
from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_stat import ReleaseRecord

# Order of the records in union is important and should be from more specific to less specific
# For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
EntityRecord = Union[RecordingRecord, ReleaseRecord, ArtistRecord]


class UserEntityStatMessage(StatMessage[MultipleUserStatRecords]):
    """ Format of messages sent to the ListenBrainz Server from Spark """
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording
