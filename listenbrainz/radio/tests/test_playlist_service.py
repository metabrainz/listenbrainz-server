import uuid
from unittest.mock import patch, MagicMock

import pytest

from listenbrainz.radio.playlist import LBRadioPlaylistService

PLAYLIST_MBID = "12345678-1234-1234-1234-123456789abc"
CREATOR = "testuser"
COLLABORATOR = "collab_user"
AUTH_TOKEN = "validtoken"

REC_MBID_1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
REC_MBID_2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

CREATOR_ID = 1
COLLABORATOR_ID = 2


def _make_playlist(public=True, creator=CREATOR, recording_mbids=None,
                   creator_id=CREATOR_ID, collaborator_ids=None):
    if recording_mbids is None:
        recording_mbids = [REC_MBID_1, REC_MBID_2]
    playlist = MagicMock()
    playlist.public = public
    playlist.creator = creator
    playlist.creator_id = creator_id
    playlist.collaborator_ids = collaborator_ids or []
    playlist.recordings = [MagicMock(mbid=m) for m in recording_mbids]
    playlist.is_visible_by.side_effect = lambda uid: (
        public or uid == creator_id or uid in (collaborator_ids or [])
    )
    return playlist


class TestLBRadioPlaylistService:

    def test_slug(self):
        assert LBRadioPlaylistService().slug == "playlist"

    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_public_playlist_returns_mbids(self, mock_get):
        mock_get.return_value = _make_playlist(public=True)
        result = LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token=None)
        assert result == [str(REC_MBID_1), str(REC_MBID_2)]

    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_not_found_raises(self, mock_get):
        mock_get.return_value = None
        with pytest.raises(RuntimeError, match="Cannot find playlist"):
            LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token=None)

    @patch("listenbrainz.radio.playlist.db_user.get_by_token", return_value={"id": CREATOR_ID})
    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_private_playlist_accessible_by_creator(self, mock_get, _mock_user):
        mock_get.return_value = _make_playlist(public=False, creator_id=CREATOR_ID)
        result = LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token=AUTH_TOKEN)
        assert result == [str(REC_MBID_1), str(REC_MBID_2)]

    @patch("listenbrainz.radio.playlist.db_user.get_by_token",
           return_value={"id": COLLABORATOR_ID})
    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_private_playlist_accessible_by_collaborator(self, mock_get, _mock_user):
        mock_get.return_value = _make_playlist(
            public=False, creator_id=CREATOR_ID, collaborator_ids=[COLLABORATOR_ID]
        )
        result = LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token="collabtoken")
        assert result == [str(REC_MBID_1), str(REC_MBID_2)]

    @patch("listenbrainz.radio.playlist.db_user.get_by_token", return_value={"id": 99})
    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_private_playlist_with_unrelated_user_raises(self, mock_get, _mock_user):
        mock_get.return_value = _make_playlist(public=False, creator_id=CREATOR_ID)
        with pytest.raises(RuntimeError, match="private"):
            LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token="othertoken")

    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_private_playlist_without_token_raises(self, mock_get):
        mock_get.return_value = _make_playlist(public=False, creator_id=CREATOR_ID)
        with pytest.raises(RuntimeError, match="private"):
            LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token=None)

    @patch("listenbrainz.radio.playlist.db_playlist.get_by_mbid")
    def test_empty_playlist_returns_empty_list(self, mock_get):
        mock_get.return_value = _make_playlist(recording_mbids=[])
        result = LBRadioPlaylistService().fetch(PLAYLIST_MBID, auth_token=None)
        assert result == []
