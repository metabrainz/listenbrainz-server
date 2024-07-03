""" This module tests data dump creation and import functions
in listenbrainz.db.dump
"""

# listenbrainz-server - Server for the ListenBrainz project
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import subprocess
import tarfile

import orjson

import listenbrainz.db as db
import listenbrainz.db.dump as db_dump
import listenbrainz.db.user as db_user
import os
import os.path
import shutil
import tempfile
import listenbrainz.db.feedback as db_feedback

from datetime import datetime

from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz.db import timescale
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.tests.utils import insert_test_stats, delete_all_couch_databases
from listenbrainz.webserver import create_app
from listenbrainz.db.model.feedback import Feedback


class DumpTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()
        self.tempdir_private = tempfile.mkdtemp()
        self.app = create_app()
        self.ts_conn = timescale.engine.connect()

    def tearDown(self):
        self.ts_conn.close()
        shutil.rmtree(self.tempdir)
        super().tearDown()

    def test_create_private_dump(self):
        time_now = datetime.today()
        dump_location = db_dump.create_private_dump(self.tempdir, time_now)
        self.assertTrue(os.path.isfile(dump_location))

    def test_create_stats_dump(self):
        all_stats = {
            f"{stat_type}_{stat_range}"
            for stat_type in ["artists", "recordings", "releases", "daily_activity", "listening_activity"]
            for stat_range in ALLOWED_STATISTICS_RANGE
        }

        data, from_ts1, to_ts1, from_ts2, to_ts2 = insert_test_stats("artists", "week", "user_top_artists_db_data_for_api_test_week.json")
        data[0]["from_ts"] = from_ts1
        data[1]["from_ts"] = from_ts1
        data[0]["to_ts"] = to_ts1
        data[1]["to_ts"] = to_ts1

        time_now = datetime.today()
        with self.app.app_context():
            dump_location = db_dump.create_statistics_dump(self.tempdir, time_now)
        self.assertTrue(os.path.isfile(dump_location))

        found = set()
        found_stats = None
        xz_command = ['xz', '--decompress', '--stdout', dump_location, '-T4']
        xz = subprocess.Popen(xz_command, stdout=subprocess.PIPE)
        with tarfile.open(fileobj=xz.stdout, mode='r|') as tar:
            for member in tar:
                file_name = member.name.split('/')[-1]
                if file_name.endswith(".jsonl"):
                    found.add(file_name[:-6])
                if file_name == "artists_week.jsonl":
                    f = tar.extractfile(member)
                    found_stats = [orjson.loads(line) for line in f.read().splitlines()]
                    for stat in found_stats:
                        del stat["last_updated"]

        self.assertEqual(all_stats, found)
        self.assertEqual(data, found_stats)

        delete_all_couch_databases()

    def test_add_dump_entry(self):
        prev_dumps = db_dump.get_dump_entries()
        db_dump.add_dump_entry(datetime.today().strftime('%s'))
        now_dumps = db_dump.get_dump_entries()
        self.assertEqual(len(now_dumps), len(prev_dumps) + 1)

    def test_copy_table(self):
        db_dump.add_dump_entry(datetime.today().strftime('%s'))
        with db.engine.connect() as connection:
            db_dump.copy_table(
                cursor=connection.connection.cursor(),
                location=self.tempdir,
                columns=['id', 'created'],
                table_name='data_dump',
            )
        dumps = db_dump.get_dump_entries()
        with open(os.path.join(self.tempdir, 'data_dump'), 'r') as f:
            file_contents = [line for line in f]
        self.assertEqual(len(dumps), len(file_contents))

    def test_import_postgres_db(self):

        # create a user
        with self.app.app_context():
            one_id = db_user.create(self.db_conn, 1, 'test_user')
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)

            # do a db dump and reset the db
            private_dump, public_dump = db_dump.dump_postgres_db(self.tempdir, self.tempdir_private)
            self.reset_db()
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 0)

            # import the dump
            db_dump.import_postgres_dump(private_dump, None, public_dump, None)
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)

            # reset again, and use more threads to import
            self.reset_db()
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 0)

            db_dump.import_postgres_dump(private_dump, None, public_dump, None, threads=2)
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)
            two_id = db_user.create(self.db_conn, 2, 'vnskprk')
            self.assertGreater(two_id, one_id)

    def test_dump_recording_feedback(self):

        # create a user
        with self.app.app_context():
            one_id = db_user.create(self.db_conn, 1, 'test_user')
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)

            # insert a feedback record
            feedback = Feedback(
                    user_id=one_id,
                    recording_msid="d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                    score=1
                )
            db_feedback.insert(self.db_conn, feedback)

            # do a db dump and reset the db
            private_dump, public_dump = db_dump.dump_postgres_db(self.tempdir, self.tempdir_private)
            self.reset_db()
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 0)
            self.assertEqual(db_feedback.get_feedback_count_for_user(self.db_conn, user_id=one_id), 0)

            # import the dump and check the records are inserted
            db_dump.import_postgres_dump(private_dump, None, public_dump, None)
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)

            dumped_feedback = db_feedback.get_feedback_for_user(
                self.db_conn, self.ts_conn, user_id=one_id, limit=1, offset=0
            )
            self.assertEqual(len(dumped_feedback), 1)
            self.assertEqual(dumped_feedback[0].user_id, feedback.user_id)
            self.assertEqual(dumped_feedback[0].recording_msid, feedback.recording_msid)
            self.assertEqual(dumped_feedback[0].score, feedback.score)

            # reset again, and use more threads to import
            self.reset_db()
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 0)
            dumped_feedback = []

            db_dump.import_postgres_dump(private_dump, None, public_dump, None, threads=2)
            user_count = db_user.get_user_count(self.db_conn)
            self.assertEqual(user_count, 1)

            dumped_feedback = db_feedback.get_feedback_for_user(
                self.db_conn, self.ts_conn, user_id=one_id, limit=1, offset=0
            )
            self.assertEqual(len(dumped_feedback), 1)
            self.assertEqual(dumped_feedback[0].user_id, feedback.user_id)
            self.assertEqual(dumped_feedback[0].recording_msid, feedback.recording_msid)
            self.assertEqual(dumped_feedback[0].score, feedback.score)

    def test_parse_ftp_name_with_id(self):
        parts = db_dump._parse_ftp_name_with_id('listenbrainz-dump-712-20220201-040003-full')
        self.assertEqual(parts[0], 712)
        self.assertEqual(parts[1], datetime(2022, 2, 1, 4, 0, 3))

        # Not enough parts
        with self.assertRaises(ValueError) as ex:
            db_dump._parse_ftp_name_with_id('listenbrainz-feedback-20220207-060003-full')
        self.assertIn("expected to have", str(ex.exception))

        # Invalid date
        with self.assertRaises(ValueError) as ex:
            db_dump._parse_ftp_name_with_id('listenbrainz-dump-712-20220201-xxxxxx-full')
        self.assertIn("does not match format", str(ex.exception))

    def test_parse_ftp_name_without_id(self):
        parts = db_dump._parse_ftp_name_without_id('listenbrainz-feedback-20220207-060003-full')
        self.assertEqual(parts[0], '20220207-060003')
        self.assertEqual(parts[1], datetime(2022, 2, 7, 6, 0, 3))

        # Not enough parts
        with self.assertRaises(ValueError) as ex:
            db_dump._parse_ftp_name_without_id('listenbrainz-dump-712-20220201-040003-full')
        self.assertIn("expected to have", str(ex.exception))

        # Invalid date
        with self.assertRaises(ValueError) as ex:
            db_dump._parse_ftp_name_without_id('listenbrainz-feedback-20220207-xxxxxx-full')
        self.assertIn("does not match format", str(ex.exception))
