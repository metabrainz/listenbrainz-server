import os
import uuid

from sqlalchemy import text

import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist
from listenbrainz.db.playlist import TROI_BOT_USER_ID

from listenbrainz.tests.integration import IntegrationTestCase, TIMESCALE_SQL_DIR
from listenbrainz.db import timescale
from listenbrainz.db.model.playlist import WritablePlaylist


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

        playlists, count = db_playlist.search_playlists_for_user(self.db_conn, self.ts_conn, self.user_1['id'], "testing")

        # Since playlist_2 is private, and user_1 does not have access to it, it will not

        self.assertEqual(len(playlists), 2)
        self.assertEqual(count, 2)
        self.assertEqual(playlists[0].name, playlist_3.name)
        self.assertEqual(playlists[1].name, playlist_1.name)

        playlists, count = db_playlist.search_playlists_for_user(self.db_conn, self.ts_conn, self.user_2['id'], "test")

        # Since user_2 has access to all the 4 playlists, all the playlists will be searched.

        self.assertEqual(len(playlists), 3)
        self.assertEqual(count, 3)
        self.assertEqual(playlists[0].name, playlist_3.name)
        self.assertEqual(playlists[1].name, playlist_2.name)
        self.assertEqual(playlists[2].name, playlist_1.name)

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
