from typing import List, Union, Optional

from pydantic import BaseModel, NonNegativeInt, validator, constr

from data.model.common_stat_spark import StatMessage
from data.model.validators import check_valid_uuid


class UserIdListener(BaseModel):
    """ Each individual record for a top listener of an entity

    Contains the ListenBrainz user ID and listen count.
    """
    user_id: NonNegativeInt
    listen_count: NonNegativeInt


class BaseListenerRecord(BaseModel):
    """ Common base class for entity listener stats """
    total_listen_count: NonNegativeInt
    total_user_count: NonNegativeInt
    listeners: List[UserIdListener]


class ArtistListenerRecord(BaseListenerRecord):
    """ Each individual record for top listeners of any given artist

    Contains the artist name, ListenBrainz user IDs and listen count.
    """
    artist_mbid: str
    artist_name: constr(min_length=1)

    _validate_uuids: classmethod = validator("artist_mbid", allow_reuse=True)(check_valid_uuid)


class ReleaseGroupListenerRecord(BaseListenerRecord):
    """ Each individual record for top listeners of any given release group

    Contains the release group name, artist name, relevant mbids, ListenBrainz user IDs and listen count.
    """
    release_group_mbid: str
    release_group_name: constr(min_length=1)
    artist_name: str
    caa_id: Optional[NonNegativeInt]
    caa_release_mbid: Optional[str]
    artist_mbids: List[constr(min_length=1)]

    _validate_uuids: classmethod = validator("release_group_mbid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)


EntityListenerRecord = Union[ArtistListenerRecord, ReleaseGroupListenerRecord]


class EntityListenerStatMessage(StatMessage[EntityListenerRecord]):
    """ Format of messages sent to the ListenBrainz Server """
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording


class UserNameListener(BaseModel):
    """ Each individual record for a top listener of an entity

    Contains the ListenBrainz user ID and listen count.
    """
    user_name: constr(min_length=1)
    listen_count: NonNegativeInt


class EntityListenerStatApi(BaseModel):
    """ Base class for the entity listeners stats API response """
    stats_range: constr(min_length=1)
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    last_updated: NonNegativeInt
    total_listen_count: NonNegativeInt
    listeners: List[UserNameListener]


class ArtistListenerStatApi(EntityListenerStatApi):
    """ Each individual record for top listeners of any given artist

    Contains the artist name, ListenBrainz user IDs and listen count.
    """
    artist_mbid: str
    artist_name: constr(min_length=1)
    _validate_uuids: classmethod = validator("artist_mbid", allow_reuse=True)(check_valid_uuid)


class ReleaseListenerStatApi(EntityListenerStatApi):
    """ Each individual record for top listeners of any given release group

    Contains the release group name, artist name, relevant mbids, ListenBrainz user IDs and listen count.
    """
    release_group_mbid: str
    release_group_name: constr(min_length=1)
    artist_name: str
    caa_id: Optional[NonNegativeInt]
    caa_release_mbid: Optional[str]
    artist_mbids: List[constr(min_length=1)]

    _validate_uuids: classmethod = validator("release_group_mbid", allow_reuse=True)(check_valid_uuid)
    _validate_artist_mbids: classmethod = validator("artist_mbids", each_item=True, allow_reuse=True)(check_valid_uuid)
