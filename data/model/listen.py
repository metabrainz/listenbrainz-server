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

from typing import Optional, List
import pydantic


class AdditionalInfo(pydantic.BaseModel):
    artist_mbids: Optional[List[str]]
    artist_msid: str
    discnumber: Optional[int]
    duration_ms: Optional[int]
    isrc: Optional[str]
    listening_from: Optional[str]
    recording_mbid: Optional[str]
    recording_msid: Optional[str]
    release_artist_name: Optional[str]
    release_artist_names: Optional[List[str]]
    release_group_mbid: Optional[str]
    release_mbid: Optional[str]
    release_msid: Optional[str]
    spotify_album_artist_ids: Optional[List[str]]
    spotify_album_id: Optional[str]
    spotify_artist_ids: Optional[List[str]]
    spotify_id: Optional[str]
    youtube_id: Optional[str]
    origin_url: Optional[str]
    tags: Optional[List[str]]
    track_mbid: Optional[str]
    tracknumber: Optional[int]
    work_mbids: Optional[List[str]]


class TrackMetadata(pydantic.BaseModel):
    artist_name: str
    track_name: str
    release_name: Optional[str]
    additional_info: Optional[AdditionalInfo]


# this is not an exhaustive definition
# it might need updating, please do not rely on it for validation.
class APIListen(pydantic.BaseModel):
    listened_at: Optional[int]
    user_name: Optional[str]
    inserted_at: Optional[int]
    listened_at_iso: Optional[str]
    playing_now: Optional[bool]
    track_metadata: TrackMetadata
