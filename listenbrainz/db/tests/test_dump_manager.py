""" Tests the data dump manage.py commands
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2018 MetaBrainz Foundation Inc.
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA"

import os
import shutil
import tempfile
import time

import pytest
from click.testing import CliRunner

import listenbrainz.db.dump as db_dump
import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.recommendations_cf_recording_feedback as db_rec_feedback
import listenbrainz.db.user as db_user
from listenbrainz.db import dump_manager
from listenbrainz.db.model.feedback import Feedback
from listenbrainz.db.model.recommendation_feedback import RecommendationFeedbackSubmit
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import generate_data
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app, timescale_connection


class DumpManagerTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.app = create_app()
        self.tempdir = tempfile.mkdtemp()
        self.tempdir_private = tempfile.mkdtemp()
        self.runner = CliRunner()
        self.listenstore = timescale_connection._ts
        self.user_id = db_user.create(1, 'iliekcomputers')
        self.user_name = db_user.get(self.db_conn, self.user_id)['musicbrainz_id']

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tempdir)

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def test_cleanup_dumps(self):
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-1-20180312-000001-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-2-20180312-000002-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-3-20180312-000003-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-4-20180312-000004-full'))

        for i in range(1, 50):
            create_path(os.path.join(
                self.tempdir, 'listenbrainz-dump-%d-20180312-%06d-incremental' % (i, i)))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-99-20200124-000007-incremental'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-dump-100-20200124-000008-incremental'))

        create_path(os.path.join(
            self.tempdir, 'listenbrainz-feedback-20180312-000001-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-feedback-20180312-000002-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-feedback-20180312-000003-full'))
        create_path(os.path.join(
            self.tempdir, 'listenbrainz-feedback-20180312-000004-full'))

        create_path(os.path.join(self.tempdir, 'not-a-dump'))

        dump_manager._cleanup_dumps(self.tempdir)

        newdirs = os.listdir(self.tempdir)
        self.assertNotIn('listenbrainz-dump-1-20180312-000001-full', newdirs)
        self.assertNotIn('listenbrainz-dump-2-20180312-000002-full', newdirs)

        self.assertIn('listenbrainz-dump-3-20180312-000003-full', newdirs)
        self.assertIn('listenbrainz-dump-4-20180312-000004-full', newdirs)

        self.assertNotIn(
            'listenbrainz-dump-1-20180312-000001-incremental', newdirs)
        self.assertNotIn(
            'listenbrainz-dump-2-20180312-000002-incremental', newdirs)
        self.assertNotIn(
            'listenbrainz-dump-3-20180312-000003-incremental', newdirs)
        self.assertNotIn(
            'listenbrainz-dump-21-20180312-000003-incremental', newdirs)

        for i in range(22, 50):
            self.assertIn(
                'listenbrainz-dump-%d-20180312-%06d-incremental' % (i, i), newdirs)

        self.assertIn(
            'listenbrainz-dump-99-20200124-000007-incremental', newdirs)
        self.assertIn(
            'listenbrainz-dump-100-20200124-000008-incremental', newdirs)

        self.assertNotIn('listenbrainz-feedback-20180312-000001-full', newdirs)
        self.assertNotIn('listenbrainz-feedback-20180312-000002-full', newdirs)

        self.assertIn('listenbrainz-feedback-20180312-000003-full', newdirs)
        self.assertIn('listenbrainz-feedback-20180312-000004-full', newdirs)

        self.assertIn('not-a-dump', newdirs)

    def test_create_full_db(self):

        listens = generate_data(1, self.user_name, 1500000000, 5)
        self.listenstore.insert(listens)

        # create a full dump
        self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--location-private',
            self.tempdir_private
        ])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]

        # make sure that the dump contains a full listens dump, a public and private dump (postgres),
        # a public and private dump (timescale) and a spark dump.
        # dumps should contain the 7 archives
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                archive_count += 1
        self.assertEqual(archive_count, 5)

        private_archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir_private, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                private_archive_count += 1
        self.assertEqual(private_archive_count, 2)

    def test_create_full_dump_with_id(self):

        self.listenstore.insert(generate_data(
            1, self.user_name, 1500000000, 5))
        # if the dump ID does not exist, it should exit with a -1
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--location-private',
            self.tempdir_private,
            '--dump-id',
            1000
        ])
        self.assertEqual(result.exit_code, -1)
        # make sure no directory was created either
        self.assertEqual(len(os.listdir(self.tempdir)), 0)

        # now, add a dump entry to the database and create a dump with that specific dump id
        dump_id = db_dump.add_dump_entry(int(time.time()))
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--location-private',
            self.tempdir_private,
            '--dump-id',
            dump_id
        ])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]
        created_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(dump_id, created_dump_id)

        dump_name = os.listdir(self.tempdir_private)[0]
        created_private_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(dump_id, created_private_dump_id)

        # dumps should contain the 7 archives
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                archive_count += 1
        self.assertEqual(archive_count, 5)

        private_archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir_private, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                private_archive_count += 1
        self.assertEqual(private_archive_count, 2)

    def test_full_dump_exits_private_location(self):
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir
        ])
        self.assertEqual(result.exit_code, -1)
        self.assertIn("No location specified for creating private database and timescale dumps", self._caplog.text)

        self._caplog.clear()
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--location-private',
            self.tempdir
        ])
        self.assertEqual(result.exit_code, -1)
        self.assertIn("Location specified for public and private dumps cannot be same", self._caplog.text)

        self._caplog.clear()
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--location-private',
            os.path.join(self.tempdir, "subdir")
        ])
        self.assertEqual(result.exit_code, -1)
        self.assertIn("Private dumps location cannot be a subdirectory of public dumps location", self._caplog.text)

        self._caplog.clear()
        # no location for private dupms is required if no private dumps are being made
        result = self.runner.invoke(dump_manager.create_full, [
            '--location',
            self.tempdir,
            '--no-db',
            '--no-timescale'
        ])
        self.assertEqual(result.exit_code, 0)

    def test_create_incremental(self):
        # create a incremental dump, this won't work because the incremental dump does
        # not have a previous dump
        result = self.runner.invoke(dump_manager.create_incremental, [
                                    '--location', self.tempdir])
        self.assertEqual(result.exit_code, -1)
        self.assertEqual(len(os.listdir(self.tempdir)), 0)

        base = int(time.time())
        dump_id = db_dump.add_dump_entry(base - 60)
        print("%d dump id" % dump_id)
        self.listenstore.insert(generate_data(1, self.user_name, base - 30, 5))
        result = self.runner.invoke(dump_manager.create_incremental, [
                                    '--location', self.tempdir])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]

        # created dump ID should be one greater than previous dump's ID
        created_dump_id = int(dump_name.split('-')[2])
        print("%d created dump id" % created_dump_id)
        self.assertEqual(created_dump_id, dump_id + 1)

        # make sure that the dump contains a full listens and spark dump
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                archive_count += 1
        self.assertEqual(archive_count, 2)

    def test_create_incremental_dump_with_id(self):

        # if the dump ID does not exist, it should exit with a -1
        result = self.runner.invoke(dump_manager.create_incremental, [
                                    '--location', self.tempdir, '--dump-id', 1000])
        self.assertEqual(result.exit_code, -1)

        # create a base dump entry
        t = int(time.time())
        db_dump.add_dump_entry(t)
        self.listenstore.insert(generate_data(1, self.user_name, 1500000000, 5))

        # create a new dump ID to recreate later
        dump_id = db_dump.add_dump_entry(int(time.time()))
        # now, create a dump with that specific dump id
        result = self.runner.invoke(dump_manager.create_incremental, [
                                    '--location', self.tempdir, '--dump-id', dump_id])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]
        created_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(dump_id, created_dump_id)

        # dump should contain the listen and spark archive
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                archive_count += 1
        self.assertEqual(archive_count, 2)

    def test_create_feedback(self):

        self.user = db_user.get_or_create(1, "ernie")
        self.user2 = db_user.get_or_create(2, "bert")
        sample_feedback = [
            {
                "user_id": self.user['id'],
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "user_id": self.user2['id'],
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": -1
            }
        ]
        for fb in sample_feedback:
            db_feedback.insert(
                Feedback(
                    user_id=fb["user_id"],
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )

        rec_feedback = [
            {
                "recording_mbid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "rating": 'love',
                'user_id': self.user['id']
            },
            {
                "recording_mbid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "rating": 'bad_recommendation',
                "user_id": self.user['id']
            },
            {
                "recording_mbid": "922eb00d-9ead-42de-aec9-8f8c1509413d",
                "rating": 'hate',
                "user_id": self.user2['id']
            }
        ]
        for fb in rec_feedback:
            db_rec_feedback.insert(
                RecommendationFeedbackSubmit(
                    user_id=fb['user_id'],
                    recording_mbid=fb["recording_mbid"],
                    rating=fb["rating"]
                )
            )

        # create a feedback dump
        self.runner.invoke(dump_manager.create_feedback,
                           ['--location', self.tempdir])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]

        # make sure that the dump contains a feedback dump
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz') or file_name.endswith(".tar"):
                archive_count += 1
        self.assertEqual(archive_count, 1)
