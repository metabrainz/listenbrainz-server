# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2021 Param Singh <me@param.codes>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from pydantic import BaseModel, validator, NonNegativeInt, constr
from listenbrainz.db.model.validators import check_valid_uuid

from datetime import datetime
from enum import Enum
from typing import Union, Optional

from data.model.listen import APIListen


class UserTimelineEventType(Enum):
    RECORDING_RECOMMENDATION = 'recording_recommendation'
    FOLLOW = 'follow'
    LISTEN = 'listen'
    NOTIFICATION = 'notification'


class RecordingRecommendationMetadata(BaseModel):
    artist_name: str
    track_name: str
    release_name: Optional[str]
    recording_mbid: Optional[str]
    recording_msid: constr(min_length=1)
    artist_msid: constr(min_length=1)

    _validate_uuids: classmethod = validator(
        "recording_mbid",
        "recording_msid",
        "artist_msid",
        allow_reuse=True
    )(check_valid_uuid)


class NotificationMetadata(BaseModel):
    creator: str
    message: str


UserTimelineEventMetadata = Union[RecordingRecommendationMetadata, NotificationMetadata]


class UserTimelineEvent(BaseModel):
    id: NonNegativeInt
    user_id: NonNegativeInt
    metadata: UserTimelineEventMetadata
    event_type: UserTimelineEventType
    created: Optional[datetime]


class APINotificationEvent(BaseModel):
    message: str


class APIFollowEvent(BaseModel):
    user_name_0: str
    user_name_1: str
    relationship_type: str
    created: NonNegativeInt


APIEventMetadata = Union[APIListen, APIFollowEvent, APINotificationEvent]


class APITimelineEvent(BaseModel):
    event_type: UserTimelineEventType
    user_name: str
    created: NonNegativeInt
    metadata: APIEventMetadata
