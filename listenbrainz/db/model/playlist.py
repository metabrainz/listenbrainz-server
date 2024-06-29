import uuid
import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/"
PLAYLIST_ARTIST_URI_PREFIX = "https://musicbrainz.org/artist/"
PLAYLIST_RELEASE_URI_PREFIX = "https://musicbrainz.org/release/"
PLAYLIST_URI_PREFIX = "https://listenbrainz.org/playlist/"
PLAYLIST_EXTENSION_URI = "https://musicbrainz.org/doc/jspf#playlist"
PLAYLIST_TRACK_EXTENSION_URI = "https://musicbrainz.org/doc/jspf#track"


class PlaylistRecording(BaseModel):
    """A recording that is part of a playlist"""
    # Internal id of the playlist
    id: NonNegativeInt
    # What playlist this recording is a part of
    playlist_id: NonNegativeInt
    # The position of this item in the playlist
    position: NonNegativeInt
    # The item
    mbid: uuid.UUID
    # Who added this item to the playlist
    added_by_id: NonNegativeInt
    # When the item was added
    created: datetime.datetime

    artist_credit: Optional[str]
    artist_mbids: Optional[List[uuid.UUID]]
    title: Optional[str]
    # What release would this be if the recording is of more than one?
    release_mbid: Optional[uuid.UUID]
    release_name: Optional[str]
    release_track_number: Optional[NonNegativeInt]  # exists in xspf, probably not needed?
    duration_ms: Optional[NonNegativeInt]
    image: Optional[str]  # who looks this up on CAA?

    additional_metadata: Optional[Dict] = None

    # Computed
    added_by: constr(min_length=1)


class WritablePlaylistRecording(PlaylistRecording):
    id: NonNegativeInt = None
    playlist_id: NonNegativeInt = None
    position: NonNegativeInt = None
    created: datetime.datetime = None
    added_by: str = None


class Playlist(BaseModel):

    # Database fields
    # The internal ID of the playlist row in the database
    id: NonNegativeInt
    # The public-facing uuid of the playlist
    mbid: uuid.UUID
    # The listenbrainz user id who created this playlist
    creator_id: NonNegativeInt
    # The name of the playlist
    name: constr(min_length=1)
    # An optional description of the playlist
    description: Optional[str]
    public: bool = True
    # When the playlist was created
    created: datetime.datetime
    # When a change was made to metadata
    last_updated: Optional[datetime.datetime]
    # If the playlist was copied from another one, the id of that playlist
    copied_from_id: Optional[NonNegativeInt]
    # If the playlist was created by a bot, the user for who this playlist was created
    created_for_id: Optional[NonNegativeInt]
    # to store extra data about the playlist
    additional_metadata: Optional[Dict]
    # The users who have permission to collaborate on this playlist
    # TODO: Because the id list isn't an FK to a table, we can't guarantee that these values
    #  actually exist. There's no agreement between collaborator_ids and collaborators.
    #  Ideally this should be a list of a User object that allows us to keep these values in sync
    collaborator_ids: List[NonNegativeInt] = []
    collaborators: List[str] = []

    # Computed fields
    created_for: Optional[str]
    creator: constr(min_length=1)
    recordings: List[PlaylistRecording]
    # mbid of the playlist referred to in copied_from_id
    copied_from_mbid: Optional[uuid.UUID]

    def is_visible_by(self, user_id: Optional[int]):
        """Check if user is allowed to access a playlist

        user_id may be None, for example if the user is not logged in.

        Args:
            user_id : (Optional) row id of the user.
        """
        if self.public:
            return True
        if user_id:
            if user_id == self.creator_id:
                return True
            elif user_id in self.collaborator_ids:
                return True
        return False

    def is_modifiable_by(self, user_id: int):
        """Check if user can modify a playlist

        Check if a user is allowed to add/move/delete items in a playlist.
        user_id is required, since playlist modifications require a logged in user

        Args:
            user_id : row id of the user.
        """
        if user_id == self.creator_id or user_id in self.collaborator_ids:
            return True
        return False

    def serialize_jspf(self):
        """ Given a playlist, return a properly formated dict that can be passed to jsonify. """

        pl = {
            "creator": self.creator,
            "title": self.name,
            "identifier": PLAYLIST_URI_PREFIX + str(self.mbid),
            "date": self.created.astimezone(datetime.timezone.utc).isoformat()
        }
        if self.description:
            pl["annotation"] = self.description

        extension = {"public": self.public, "creator": self.creator}
        if self.last_updated:
            extension["last_modified_at"] = self.last_updated.astimezone(datetime.timezone.utc).isoformat()
        if self.copied_from_id is not None:
            if self.copied_from_mbid is None:
                extension['copied_from_deleted'] = True
            else:
                extension['copied_from_mbid'] = PLAYLIST_URI_PREFIX + str(self.copied_from_mbid)
        if self.created_for_id:
            extension['created_for'] = self.created_for
        if self.collaborators:
            extension['collaborators'] = self.collaborators
        if self.additional_metadata:
            extension['additional_metadata'] = self.additional_metadata

        pl["extension"] = {PLAYLIST_EXTENSION_URI: extension}

        tracks = []
        for rec in self.recordings:
            tr = {"identifier": [PLAYLIST_TRACK_URI_PREFIX + str(rec.mbid)]}
            if rec.artist_credit:
                tr["creator"] = rec.artist_credit

            if rec.release_name:
                tr["album"] = rec.release_name

            if rec.title:
                tr["title"] = rec.title

            if rec.duration_ms:
                tr["duration"] = rec.duration_ms

            extension = {"added_by": rec.added_by, "added_at": rec.created.astimezone(datetime.timezone.utc).isoformat()}
            if rec.artist_mbids:
                extension["artist_identifiers"] = [PLAYLIST_ARTIST_URI_PREFIX + str(mbid) for mbid in rec.artist_mbids]

            if rec.release_mbid:
                extension["release_identifier"] = PLAYLIST_RELEASE_URI_PREFIX + str(rec.release_mbid)

            if rec.additional_metadata:
                extension["additional_metadata"] = rec.additional_metadata

            tr["extension"] = {PLAYLIST_TRACK_EXTENSION_URI: extension}
            tracks.append(tr)

        pl["track"] = tracks

        return {"playlist": pl}


class WritablePlaylist(Playlist):
    id: int = None
    mbid: Optional[str]
    creator: str = None
    recordings: List[PlaylistRecording] = []
    created: datetime.datetime = None

    _validate_mbid: classmethod = validator("mbid", allow_reuse=True)(check_valid_uuid)
