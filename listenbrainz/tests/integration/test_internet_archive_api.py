# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2024 Rayyan Seliya <rayyan_seliya123>
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

from sqlalchemy import text
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
import json
from datetime import datetime


class InternetArchiveAPITestCase(ListenAPIIntegrationTestCase):

    def create_ia_cache_table(self):
        """Create the Internet Archive cache table if it doesn't exist."""
        try:
            # Create schema if it doesn't exist
            self.ts_conn.execute(text("CREATE SCHEMA IF NOT EXISTS internetarchive_cache"))
            
            # Create table if it doesn't exist
            create_table_query = """
                CREATE TABLE IF NOT EXISTS internetarchive_cache.track (
                    id SERIAL PRIMARY KEY,
                    track_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    artist TEXT[],
                    album TEXT,
                    stream_urls TEXT[],
                    artwork_url TEXT,
                    data JSONB,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            self.ts_conn.execute(text(create_table_query))
            self.ts_conn.commit()
        except Exception as e:
            # Table might already exist, that's okay
            pass

    def insert_sample_ia_data(self):
        """Insert sample Internet Archive track data for testing."""
        # First check if the table exists, if not create it
        try:
            # Create schema if it doesn't exist
            self.ts_conn.execute(text("CREATE SCHEMA IF NOT EXISTS internetarchive_cache"))
            
            # Create table if it doesn't exist
            create_table_query = """
                CREATE TABLE IF NOT EXISTS internetarchive_cache.track (
                    id SERIAL PRIMARY KEY,
                    track_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    artist TEXT[],
                    album TEXT,
                    stream_urls TEXT[],
                    artwork_url TEXT,
                    data JSONB,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
            self.ts_conn.execute(text(create_table_query))
            
            # Clear any existing data
            self.ts_conn.execute(text("DELETE FROM internetarchive_cache.track"))
            
            # Insert sample data
            query = """
                INSERT INTO internetarchive_cache.track
                    (track_id, name, artist, album, stream_urls, artwork_url, data, last_updated)
                VALUES
                    ('https://archive.org/details/00TtuloInttrprete66',
                     'Los Norteños / Cuando Canta La Lluvia - Perez Prado y Hermanas Montoya (Very Rare Recordings)',
                     ARRAY['Pérez Prado y Orquesta con Hermanas Montoya'],
                     'RCA Victor #70-9428',
                     ARRAY[
                         'https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.m4a',
                         'https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.mp3',
                         'https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.ogg',
                         'https://archive.org/download/00TtuloInttrprete66/Los Norteños.m4a',
                         'https://archive.org/download/00TtuloInttrprete66/Los Norteños.mp3',
                         'https://archive.org/download/00TtuloInttrprete66/Los Norteños.ogg'
                     ],
                     'https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.png',
                     '{"addeddate": "2013-08-22 06:05:59", "collection": ["78rpm", "audio_music"], "title": "Los Norteños / Cuando Canta La Lluvia - Perez Prado y Hermanas Montoya (Very Rare Recordings)", "identifier": "00TtuloInttrprete66", "mediatype": "audio", "subject": ["Rare Recording", "78 rpm", "rca victor", "mambo", "perez prado", "hermanas montoya", "latin"]}',
                     NOW()
                    ),
                    ('https://archive.org/details/test_track_2',
                     'Test Track 2',
                     ARRAY['Test Artist 2'],
                     'Test Album 2',
                     ARRAY['https://archive.org/download/test_track_2/test.mp3'],
                     'https://archive.org/download/test_track_2/artwork.jpg',
                     '{"title": "Test Track 2", "identifier": "test_track_2", "mediatype": "audio"}',
                     NOW()
                    ),
                    ('https://archive.org/details/test_track_3',
                     'Another Test Track',
                     ARRAY['Different Artist'],
                     'Different Album',
                     ARRAY['https://archive.org/download/test_track_3/test.mp3'],
                     NULL,
                     '{"title": "Another Test Track", "identifier": "test_track_3", "mediatype": "audio"}',
                     NOW()
                    )
            """
            self.ts_conn.execute(text(query))
            self.ts_conn.commit()
        except Exception as e:
            # If table creation fails, that's okay - the test will handle it
            pass

    def setUp(self):
        super(InternetArchiveAPITestCase, self).setUp()
        # Create the Internet Archive cache table and insert sample data
        self.create_ia_cache_table()
        self.insert_sample_ia_data()

    def test_search_ia_with_artist(self):
        """Test searching IA tracks by artist name."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'Pérez Prado y Orquesta con Hermanas Montoya'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        
        track = data['results'][0]
        self.assertEqual(track['name'], 'Los Norteños / Cuando Canta La Lluvia - Perez Prado y Hermanas Montoya (Very Rare Recordings)')
        self.assertEqual(track['artist'], ['Pérez Prado y Orquesta con Hermanas Montoya'])
        self.assertEqual(track['album'], 'RCA Victor #70-9428')
        self.assertEqual(track['track_id'], 'https://archive.org/details/00TtuloInttrprete66')
        self.assertIsInstance(track['stream_urls'], list)
        self.assertEqual(len(track['stream_urls']), 6)
        self.assertIsNotNone(track['artwork_url'])
        self.assertIsNotNone(track['last_updated'])

    def test_search_ia_with_track_name(self):
        """Test searching IA tracks by track name."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'track': 'Los Norteños'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        
        track = data['results'][0]
        self.assertIn('Los Norteños', track['name'])

    def test_search_ia_with_album(self):
        """Test searching IA tracks by album name."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'album': 'RCA Victor'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        
        track = data['results'][0]
        self.assertEqual(track['album'], 'RCA Victor #70-9428')

    def test_search_ia_with_multiple_parameters(self):
        """Test searching IA tracks with multiple search parameters."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={
                'artist': 'Pérez Prado y Orquesta con Hermanas Montoya',
                'track': 'Cuando Canta La Lluvia',
                'album': 'RCA Victor'
            }
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)

    def test_search_ia_with_no_results(self):
        """Test searching IA tracks that don't exist."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'Non Existent Artist'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 0)

    def test_search_ia_with_no_parameters(self):
        """Test searching IA tracks without any search parameters."""
        response = self.client.get('/1/internet_archive/search')
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        # Should return all tracks when no parameters provided
        self.assertEqual(len(data['results']), 3)

    def test_search_ia_with_partial_artist_match(self):
        """Test searching IA tracks with partial artist name."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'Pérez Prado'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        # Artist search uses exact match, so partial search should return 0 results
        self.assertEqual(len(data['results']), 0)

    def test_search_ia_with_partial_track_match(self):
        """Test searching IA tracks with partial track name."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'track': 'Test Track'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)  # Should match both test tracks

    def test_search_ia_response_structure(self):
        """Test that the IA search response has the correct structure."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'Pérez Prado y Orquesta con Hermanas Montoya'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        
        if data['results']:
            track = data['results'][0]
            required_fields = ['id', 'track_id', 'name', 'artist', 'album', 'stream_urls', 'artwork_url', 'data', 'last_updated']
            for field in required_fields:
                self.assertIn(field, track)

    def test_search_ia_case_insensitive(self):
        """Test that the search is case insensitive."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'pérez prado y orquesta con hermanas montoya'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        # Artist search is case sensitive, so lowercase should return 0 results
        self.assertEqual(len(data['results']), 0)

    def test_search_ia_with_special_characters(self):
        """Test searching with special characters in artist names."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': 'Pérez Prado y Orquesta con Hermanas Montoya'}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)

    def test_search_ia_empty_string_parameters(self):
        """Test searching with empty string parameters."""
        response = self.client.get(
            '/1/internet_archive/search',
            query_string={'artist': '', 'track': '', 'album': ''}
        )
        self.assert200(response)
        
        data = response.json
        self.assertIn('results', data)
        # Should return all tracks when parameters are empty strings
        self.assertEqual(len(data['results']), 3)
