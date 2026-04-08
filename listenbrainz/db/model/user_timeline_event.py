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

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Union, Optional, List

from pydantic import BaseModel, Field

from data.model.listen import APIListen, TrackMetadata
from listenbrainz.db.model.review import CBReviewTimelineMetadata
from listenbrainz.db.msid_mbid_mapping import MsidMbidModel


class UserTimelineEventType(StrEnum):
    RECORDING_RECOMMENDATION = 'recording_recommendation'
    FOLLOW = 'follow'
    LISTEN = 'listen'
    NOTIFICATION = 'notification'
    RECORDING_PIN = 'recording_pin'
    CRITIQUEBRAINZ_REVIEW = 'critiquebrainz_review'
    PERSONAL_RECORDING_RECOMMENDATION = 'personal_recording_recommendation'
    THANKS = 'thanks'


class RecordingRecommendationMetadata(MsidMbidModel):
    pass


# while creating a personal recommendation, at least one user is required but the user might
# delete their account in future, causing the list to become empty. use different models for
# reading and writing to avoid errors.
class WritePersonalRecordingRecommendationMetadata(MsidMbidModel):
    users: Annotated[list[str], Field(min_length=1)]
    blurb_content: Optional[str] = None


class PersonalRecordingRecommendationMetadata(MsidMbidModel):
    users: list[str]
    blurb_content: Optional[str] = None


class NotificationMetadata(BaseModel):
    creator: Annotated[str, Field(min_length=1)]
    message: Annotated[str, Field(min_length=1)]


class ThanksMetadata(BaseModel):
    original_event_type: UserTimelineEventType
    original_event_id: int = Field(ge=0)
    blurb_content: Optional[str]

class ThanksEventMetadata(BaseModel):
    original_event_type: UserTimelineEventType
    original_event_id: int = Field(ge=0)
    blurb_content: Optional[str]
    thanker_id: int = Field(ge=0)
    thanker_username: Annotated[str, Field(min_length=1)]
    thankee_id: int = Field(ge=0)
    thankee_username: Annotated[str, Field(min_length=1)]


UserTimelineEventMetadata = Union[CBReviewTimelineMetadata, PersonalRecordingRecommendationMetadata,
                                  RecordingRecommendationMetadata, NotificationMetadata, ThanksEventMetadata]


class UserTimelineEvent(BaseModel):
    id: int = Field(ge=0)
    user_id: int = Field(ge=0)
    metadata: UserTimelineEventMetadata
    event_type: UserTimelineEventType
    created: Optional[datetime]
    user_name: Optional[str]


class APINotificationEvent(BaseModel):
    message: Annotated[str, Field(min_length=1)]


class APIFollowEvent(BaseModel):
    user_name_0: Annotated[str, Field(min_length=1)]
    user_name_1: Annotated[str, Field(min_length=1)]
    relationship_type: Annotated[str, Field(min_length=1)]
    created: int = Field(ge=0)


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
    users: List[str]
    blurb_content: Optional[str]
    track_metadata: TrackMetadata

class APIThanksEvent(BaseModel):
    created: int = Field(ge=0)
    blurb_content: Optional[str]
    original_event_id: int = Field(ge=0)
    original_event_type: str
    thanker_id: int = Field(ge=0)
    thanker_username: Annotated[str, Field(min_length=1)]
    thankee_id: int = Field(ge=0)
    thankee_username: Annotated[str, Field(min_length=1)]


APIEventMetadata = Union[APIPersonalRecommendationEvent, APIListen, APIFollowEvent, APINotificationEvent, APIPinEvent, APICBReviewEvent, APIThanksEvent]


class APITimelineEvent(BaseModel):
    id: Optional[int]
    event_type: UserTimelineEventType
    user_name: Annotated[str, Field(min_length=1)]
    created: int = Field(ge=0)
    metadata: APIEventMetadata
    hidden: bool

class SimilarUserTimelineEvent(APITimelineEvent):
    similarity: float | None = None

class HiddenUserTimelineEvent(BaseModel):
    id: int = Field(ge=0)
    user_id: int = Field(ge=0)
    event_type: UserTimelineEventType
    event_id: int = Field(ge=0)
    created: datetime
