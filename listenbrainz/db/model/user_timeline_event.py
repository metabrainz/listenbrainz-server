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

from pydantic import BaseModel, NonNegativeInt, constr, conlist

from datetime import datetime
from enum import Enum
from typing import Union, Optional, List

from data.model.listen import APIListen
from listenbrainz.db.model.review import CBReviewTimelineMetadata
from listenbrainz.db.msid_mbid_mapping import MsidMbidModel


class UserTimelineEventType(Enum):
    RECORDING_RECOMMENDATION = 'recording_recommendation'
    FOLLOW = 'follow'
    LISTEN = 'listen'
    NOTIFICATION = 'notification'
    RECORDING_PIN = 'recording_pin'
    CRITIQUEBRAINZ_REVIEW = 'critiquebrainz_review'
    PERSONAL_RECORDING_RECOMMENDATION = 'personal_recording_recommendation'


class RecordingRecommendationMetadata(MsidMbidModel):
    artist_name: constr(min_length=1)
    track_name: constr(min_length=1)
    release_name: Optional[str]


class PersonalRecordingRecommendationMetadata(RecordingRecommendationMetadata):
    users: conlist(str, min_items=1)
    blurb_content: Optional[str]


class NotificationMetadata(BaseModel):
    creator: constr(min_length=1)
    message: constr(min_length=1)


UserTimelineEventMetadata = Union[CBReviewTimelineMetadata, PersonalRecordingRecommendationMetadata,
                                  RecordingRecommendationMetadata, NotificationMetadata]


class UserTimelineEvent(BaseModel):
    id: NonNegativeInt
    user_id: NonNegativeInt
    metadata: UserTimelineEventMetadata
    event_type: UserTimelineEventType
    created: Optional[datetime]
    user_name: Optional[str]


class APINotificationEvent(BaseModel):
    message: constr(min_length=1)


class APIFollowEvent(BaseModel):
    user_name_0: constr(min_length=1)
    user_name_1: constr(min_length=1)
    relationship_type: constr(min_length=1)
    created: NonNegativeInt


class APIPinEvent(APIListen):
    blurb_content: Optional[str]


class APICBReviewEvent(BaseModel):
    user_name: str
    entity_name: str
    entity_id: str
    entity_type: str
    rating: Optional[int]
    text: str
    review_mbid: str


class APIPersonalRecommendationEvent(BaseModel):
    artist_name: constr(min_length=1)
    track_name: constr(min_length=1)
    release_name: Optional[str]
    recording_mbid: Optional[str]
    recording_msid: constr(min_length=1)
    users: List[str]
    blurb_content: Optional[str]


APIEventMetadata = Union[APIListen, APIFollowEvent, APINotificationEvent, APIPinEvent, APICBReviewEvent, APIPersonalRecommendationEvent]


class APITimelineEvent(BaseModel):
    id: Optional[int]
    event_type: UserTimelineEventType
    user_name: constr(min_length=1)
    created: NonNegativeInt
    metadata: APIEventMetadata
    hidden: bool


class HiddenUserTimelineEvent(BaseModel):
    id: NonNegativeInt
    user_id: NonNegativeInt
    event_type: UserTimelineEventType
    event_id: NonNegativeInt
    created: datetime
