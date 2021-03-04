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
from enum import Enum
from typing import Union, Optional

import pydantic


class UserTimelineEventType(Enum):
    RECORDING_RECOMMENDATION = 'recording_recommendation'


class RecordingRecommendationMetadata(pydantic.BaseModel):
    artist_name: str
    track_name: str
    release_name: Optional[str]
    recording_mbid: Optional[str]
    recording_msid: str
    artist_msid: str


UserTimelineEventMetadata = Union[RecordingRecommendationMetadata]


class UserTimelineEvent(pydantic.BaseModel):
    id: int
    user_id: int
    metadata: UserTimelineEventMetadata
    event_type: UserTimelineEventType
    created: Optional[datetime]
