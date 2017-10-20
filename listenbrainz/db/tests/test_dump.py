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

import listenbrainz.db as db
import listenbrainz.db.dump as db_dump
import listenbrainz.db.user as db_user
import os
import os.path
import shutil
import sqlalchemy
import tempfile

from datetime import datetime
from listenbrainz.db.testing import DatabaseTestCase

class DumpTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()


    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tempdir)


    def test_create_private_dump(self):
        time_now = datetime.today()
        dump_location = db_dump.create_private_dump(self.tempdir, time_now)
        self.assertTrue(os.path.isfile(dump_location))


    def test_create_stats_dump(self):
        time_now = datetime.today()
        dump_location = db_dump.create_private_dump(self.tempdir, time_now)
        self.assertTrue(os.path.isfile(dump_location))


    def test_add_dump_entry(self):
        prev_dumps = db_dump.get_dump_entries()
        db_dump.add_dump_entry()
        now_dumps = db_dump.get_dump_entries()
        self.assertEqual(len(now_dumps), len(prev_dumps) + 1)

    def test_copy_table(self):
        db_dump.add_dump_entry()
        db_dump.copy_table(self.tempdir, 'data_dump')
        dumps = db_dump.get_dump_entries()
        with open(os.path.join(self.tempdir, 'data_dump'), 'r') as f:
            file_contents = [line for line in f]
        self.assertEqual(len(dumps), len(file_contents))

    def test_import_postgres_db(self):

        # create a user
        db_user.create('test_user')
        user_count = db_user.get_user_count()
        self.assertEqual(user_count, 1)

        # do a db dump and reset the db
        location = db_dump.dump_postgres_db(self.tempdir)
        self.reset_db()
        user_count = db_user.get_user_count()
        self.assertEqual(user_count, 0)

        # import the dump
        db_dump.import_postgres_dump(location)
        user_count = db_user.get_user_count()
        self.assertEqual(user_count, 1)


