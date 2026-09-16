import os
import uuid

from sqlalchemy import text

import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist
from listenbrainz.db.playlist import TROI_BOT_USER_ID

from listenbrainz.tests.integration import IntegrationTestCase, TIMESCALE_SQL_DIR
from listenbrainz.db import timescale
from listenbrainz.db.exceptions import InvalidUser
from listenbrainz.db.model.playlist import WritablePlaylist, WritablePlaylistRecording


RECORDING_MBIDS = [
    "e8f9b188-f819-4e43-ab0f-4bd26ce9ff56",
    "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a",
    "4a77a078-e91a-4522-a409-3b58aa7de3ae",
    "97e69767-5d34-4c97-b36a-f3b2b1ef9dae",
    "a076e8af-5791-4531-a0ef-6b0a21f8e81c",
    "cc197bad-dc9c-440d-a5b5-d52ba2e14234",
]


class PlaylistTestCase(IntegrationTestCase):

    def setUp(self):
        super(PlaylistTestCase, self).setUp()
        self.user_1 = db_user.get_or_create(self.db_conn, 1, 'ansh')
        self.user_2 = db_user.get_or_create(self.db_conn, 2, 'ansh_2')
        self.ts_conn = timescale.engine.connect()

    def tearDown(self):
        super(PlaylistTestCase, self).tearDown()
        self.ts_conn.close()
        timescale.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'reset_tables.sql'))

    def _create_empty_playlist(self):
        return db_playlist.create(self.db_conn, self.ts_conn, WritablePlaylist(
            name="test playlist",
            creator_id=self.user_1['id'],
            description="for insert_recordings tests",
            collaborator_ids=[],
            collaborators=[],
            public=False,
            additional_metadata={},
        ))

    def _make_recordings(self, mbids, added_by_id):
        return [
            WritablePlaylistRecording(mbid=uuid.UUID(mbid), added_by_id=added_by_id)
            for mbid in mbids
        ]

    def test_insert_recordings_empty_list(self):
        """insert_recordings returns early without writing rows when given no recordings"""
        playlist = self._create_empty_playlist()

        result = db_playlist.insert_recordings(
            self.db_conn, self.ts_conn, playlist.id, [], 0
        )

        self.assertEqual(result, [])
        self.assertEqual(
            db_playlist.get_recordings_count_for_playlist(self.ts_conn, playlist.id), 0
        )

    def test_insert_recordings_bulk(self):
        """insert_recordings bulk-inserts many recordings in one query"""
        playlist = self._create_empty_playlist()
        mbids = RECORDING_MBIDS
        recordings = self._make_recordings(mbids, self.user_1['id'])

        inserted = db_playlist.insert_recordings(
            self.db_conn, self.ts_conn, playlist.id, recordings, 0
        )
        self.ts_conn.commit()

        self.assertEqual(len(inserted), len(mbids))
        for i, recording in enumerate(inserted):
            self.assertIsNotNone(recording.id)
            self.assertEqual(recording.position, i)
            self.assertEqual(recording.playlist_id, playlist.id)
            self.assertEqual(str(recording.mbid), mbids[i])
            self.assertEqual(recording.added_by, self.user_1['musicbrainz_id'])

        stored = db_playlist.get_by_mbid(self.db_conn, self.ts_conn, playlist.mbid)
        self.assertEqual(len(stored.recordings), len(mbids))
        self.assertEqual(
            [str(r.mbid) for r in stored.recordings],
            mbids,
        )
        self.assertEqual(
            db_playlist.get_recordings_count_for_playlist(self.ts_conn, playlist.id),
            len(mbids),
        )

    def test_insert_recordings_multiple_added_by(self):
        """insert_recordings resolves added_by for multiple users in one lookup"""
        playlist = self._create_empty_playlist()
        recordings = self._make_recordings(RECORDING_MBIDS[:3], self.user_1['id'])
        recordings += self._make_recordings(RECORDING_MBIDS[3:], self.user_2['id'])

        inserted = db_playlist.insert_recordings(
            self.db_conn, self.ts_conn, playlist.id, recordings, 0
        )
        self.ts_conn.commit()

        self.assertEqual(len(inserted), len(RECORDING_MBIDS))
        self.assertEqual(
            {r.added_by for r in inserted[:3]},
            {self.user_1['musicbrainz_id']},
        )
        self.assertEqual(
            {r.added_by for r in inserted[3:]},
            {self.user_2['musicbrainz_id']},
        )

    def test_insert_recordings_at_offset(self):
        """add_recordings_to_playlist inserts a batch at a non-zero position"""
        playlist = self._create_empty_playlist()
        initial = self._make_recordings(RECORDING_MBIDS[:2], self.user_1['id'])
        db_playlist.insert_recordings(self.db_conn, self.ts_conn, playlist.id, initial, 0)
        self.ts_conn.commit()

        playlist = db_playlist.get_by_mbid(self.db_conn, self.ts_conn, playlist.mbid)
        to_insert = self._make_recordings(RECORDING_MBIDS[2:5], self.user_1['id'])
        db_playlist.add_recordings_to_playlist(
            self.db_conn, self.ts_conn, playlist, to_insert, position=1
        )

        stored = db_playlist.get_by_mbid(self.db_conn, self.ts_conn, playlist.mbid)
        self.assertEqual(len(stored.recordings), 5)
        # Inserting at position 1 shifts the recording previously at 1 to position 4.
        expected_mbids = [
            RECORDING_MBIDS[0],
            RECORDING_MBIDS[2],
            RECORDING_MBIDS[3],
            RECORDING_MBIDS[4],
            RECORDING_MBIDS[1],
        ]
        self.assertEqual([str(r.mbid) for r in stored.recordings], expected_mbids)
        self.assertEqual([r.position for r in stored.recordings], [0, 1, 2, 3, 4])

    def test_create(self):
        playlist_1 = WritablePlaylist(
            name="playlist_1",
            creator_id=self.user_1['id'],
            description="playlist_1_description",
            collaborator_ids=[],
            collaborators=[],
            public=False,
            additional_metadata={}
        )
        new_playlist = db_playlist.create(self.db_conn, self.ts_conn, playlist_1)

        playlist = db_playlist.get_by_mbid(self.db_conn, self.ts_conn, new_playlist.mbid)
        self.assertEqual(playlist.name, playlist_1.name)
        self.assertEqual(playlist.creator_id, playlist_1.creator_id)
        self.assertEqual(playlist.description, playlist_1.description)

    def test_search_playlist(self):
        playlist_1 = WritablePlaylist(
            name="playlist_1",
            creator_id=self.user_1['id'],
            description="playlist_1_description",
            collaborator_ids=[self.user_2['id']],
            collaborators=["ansh_2"],
            public=False,
            additional_metadata={}
        )

        playlist_2 = WritablePlaylist(
            name="playlist_2",
            creator_id=self.user_2['id'],
            description="playlist_2_description",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={}
        )

        # Since the playlist playlist_2 is public, it should be returned in the search results

        new_playlist_1 = db_playlist.create(self.db_conn, self.ts_conn, playlist_1)
        new_playlist_2 = db_playlist.create(self.db_conn, self.ts_conn, playlist_2)

        playlists, count = db_playlist.search_playlist(self.db_conn, self.ts_conn, "playlist")

        self.assertEqual(len(playlists), 1)
        self.assertEqual(count, 1)
        self.assertEqual(playlists[0].name, playlist_2.name)

    def test_search_playlist_for_user(self):
        playlist_1 = WritablePlaylist(
            name="playlist_1",
            creator_id=self.user_1['id'],
            description="testing_1",
            collaborator_ids=[self.user_2['id']],
            collaborators=["ansh_2"],
            public=False,
            additional_metadata={}
        )

        playlist_2 = WritablePlaylist(
            name="testing_2",
            creator_id=self.user_2['id'],
            description="helloWorld",
            collaborator_ids=[],
            collaborators=[],
            public=False,
            additional_metadata={}
        )

        playlist_3 = WritablePlaylist(
            name="test playlist",
            creator_id=self.user_1['id'],
            description="helloWorld",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={}
        )

        playlist_4 = WritablePlaylist(
            name="unknown_playlist",
            creator_id=self.user_1['id'],
            description="description",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={}
        )

        new_playlist_1 = db_playlist.create(self.db_conn, self.ts_conn, playlist_1)
        new_playlist_2 = db_playlist.create(self.db_conn, self.ts_conn, playlist_2)
        new_playlist_3 = db_playlist.create(self.db_conn, self.ts_conn, playlist_3)
        new_playlist_4 = db_playlist.create(self.db_conn, self.ts_conn, playlist_4)

        playlists, count = db_playlist.search_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id'], "testing", viewer_id=self.user_1['id']
        )

        # Since playlist_2 is private, and user_1 does not have access to it, it will not

        self.assertEqual(len(playlists), 2)
        self.assertEqual(count, 2)
        self.assertEqual(playlists[0].name, playlist_3.name)
        self.assertEqual(playlists[1].name, playlist_1.name)

        playlists, count = db_playlist.search_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_2['id'], "test", viewer_id=self.user_2['id']
        )

        # Only playlists associated with user_2 should be searched.
        # user_2 is a collaborator on playlist_1 and the owner of playlist_2.

        self.assertEqual(len(playlists), 2)
        self.assertEqual(count, 2)
        self.assertEqual({p.name for p in playlists}, {playlist_1.name, playlist_2.name})

        playlists, count = db_playlist.search_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id'], "testing", viewer_id=None
        )

        # Anonymous viewer should only see public playlists associated with user_1.
        # playlist_1 is private, so only playlist_3 matches.

        self.assertEqual(len(playlists), 1)
        self.assertEqual(count, 1)
        self.assertEqual(playlists[0].name, playlist_3.name)

        playlists, count = db_playlist.search_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_2['id'], "test", viewer_id=self.user_2['id'],
            include_global=True
        )

        # With include_global=True, user_1's public playlist_3 should also appear in results
        # in addition to user_2's associated playlists (playlist_1, playlist_2).

        self.assertEqual(len(playlists), 3)
        self.assertEqual(count, 3)
        self.assertEqual({p.name for p in playlists}, {playlist_1.name, playlist_2.name, playlist_3.name})

    def test_delete_deletes_user_playlists(self):
        """Tests that deleting a user also deletes their playlists"""
        query = text('INSERT INTO "user" (id, musicbrainz_id, musicbrainz_row_id, auth_token) VALUES (:user_id, :mb_id, :mb_row_id, :token)')
        self.db_conn.execute(query, {
            "user_id": TROI_BOT_USER_ID,
            "mb_id": "troi-bot",
            "mb_row_id": TROI_BOT_USER_ID,
            "token": str(uuid.uuid4())
        })

        playlist_1 = WritablePlaylist(
            name="My Playlist",
            creator_id=self.user_1['id'],
            description="A test playlist",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={}
        )
        created_playlist_1 = db_playlist.create(self.db_conn, self.ts_conn, playlist_1)

        playlist_2 = WritablePlaylist(
            name="Another Playlist",
            creator_id=self.user_1['id'],
            description="Another test playlist",
            collaborator_ids=[],
            collaborators=[],
            public=False,
            additional_metadata={}
        )
        created_playlist_2 = db_playlist.create(self.db_conn, self.ts_conn, playlist_2)

        playlist_3 = WritablePlaylist(
            name="Recommendations",
            creator_id=TROI_BOT_USER_ID,
            created_for_id=self.user_1['id'],
            description="Playlist created for user",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={
                "algorithm_metadata": {"source_patch": "weekly-jams"},
            }
        )
        created_playlist_3 = db_playlist.create(self.db_conn, self.ts_conn, playlist_3)

        playlist_4 = WritablePlaylist(
            name="Collaborative Playlist",
            creator_id=self.user_2['id'],
            description="A collaborative playlist",
            collaborator_ids=[self.user_1['id']],
            collaborators=[],
            public=True,
            additional_metadata={}
        )
        created_playlist_4 = db_playlist.create(self.db_conn, self.ts_conn, playlist_4)

        playlists, _ = db_playlist.get_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id'], include_private=True
        )
        self.assertEqual(len(playlists), 2)
        playlists, _ = db_playlist.get_playlists_created_for_user(
            self.db_conn, self.ts_conn, self.user_1['id']
        )
        self.assertEqual(len(playlists), 1)
        playlists = db_playlist.get_recommendation_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id']
        )
        self.assertEqual(len(playlists), 1)

        db_playlist.delete_playlists_by_user_id(self.ts_conn, self.user_1['id'])
        db_user.delete(self.db_conn, self.user_1['id'])
        self.db_conn.commit()

        user = db_user.get(self.db_conn, self.user_1['id'])
        self.assertIsNone(user)
        playlists, _ = db_playlist.get_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id'], include_private=True
        )
        self.assertEqual(len(playlists), 0)
        playlists, _ = db_playlist.get_playlists_created_for_user(
            self.db_conn, self.ts_conn, self.user_1['id']
        )
        self.assertEqual(len(playlists), 0)
        playlists = db_playlist.get_recommendation_playlists_for_user(
            self.db_conn, self.ts_conn, self.user_1['id']
        )
        self.assertEqual(len(playlists), 0)

        updated_playlist = db_playlist.get_by_mbid(
            self.db_conn, self.ts_conn, created_playlist_4.mbid
        )
        self.assertIsNotNone(updated_playlist)
        self.assertNotIn(self.user_1["id"], updated_playlist.collaborator_ids)

    def test_create_playlist_invalid_user(self):
        """db_playlist.create raises InvalidUser when creator or created_for user does not exist"""
        playlist_invalid_creator = WritablePlaylist(
            name="Invalid Creator Playlist",
            creator_id=9999999,
            description="Testing invalid creator",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={},
        )
        with self.assertRaises(InvalidUser):
            db_playlist.create(self.db_conn, self.ts_conn, playlist_invalid_creator)

        playlist_invalid_created_for = WritablePlaylist(
            name="Invalid Created For Playlist",
            creator_id=self.user_1["id"],
            created_for_id=9999999,
            description="Testing invalid created_for",
            collaborator_ids=[],
            collaborators=[],
            public=True,
            additional_metadata={},
        )
        with self.assertRaises(InvalidUser):
            db_playlist.create(self.db_conn, self.ts_conn, playlist_invalid_created_for)
