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

import listenbrainz.db.dump as db_dump
import listenbrainz.db.dump_manager as dump_manager
import listenbrainz.db.user as db_user
import logging
import os
import shutil
import tempfile
import time

from click.testing import CliRunner
from listenbrainz.db import dump_manager
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import generate_data
from listenbrainz.utils import create_path
from listenbrainz.webserver import create_app
from listenbrainz.webserver.influx_connection import init_influx_connection
from time import sleep

class DumpManagerTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        app = create_app()
        self.tempdir = tempfile.mkdtemp()
        self.runner = CliRunner()
        self.listenstore = init_influx_connection(logging.getLogger(__name__), {
            'REDIS_HOST': app.config['REDIS_HOST'],
            'REDIS_PORT': app.config['REDIS_PORT'],
            'REDIS_NAMESPACE': app.config['REDIS_NAMESPACE'],
            'INFLUX_HOST': app.config['INFLUX_HOST'],
            'INFLUX_PORT': app.config['INFLUX_PORT'],
            'INFLUX_DB_NAME': app.config['INFLUX_DB_NAME'],
        })
        self.user_id = db_user.create(1, 'iliekcomputers')
        self.user_name = db_user.get(self.user_id)['musicbrainz_id']

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tempdir)

    def test_cleanup_dumps(self):
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-1-20180312-000001-full'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-2-20180312-000002-full'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-3-20180312-000003-full'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-4-20180312-000004-full'))

        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-1-20180312-000001-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-2-20180312-000002-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-3-20180312-000003-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-4-20180312-000004-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-5-20180312-000005-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-6-20180312-000006-incremental'))
        create_path(os.path.join(self.tempdir, 'listenbrainz-dump-7-20180312-000007-incremental'))

        create_path(os.path.join(self.tempdir, 'not-a-dump'))

        dump_manager._cleanup_dumps(self.tempdir)

        newdirs = os.listdir(self.tempdir)
        self.assertNotIn('listenbrainz-dump-1-20180312-000001-full', newdirs)
        self.assertNotIn('listenbrainz-dump-2-20180312-000002-full', newdirs)

        self.assertIn('listenbrainz-dump-3-20180312-000003-full', newdirs)
        self.assertIn('listenbrainz-dump-4-20180312-000004-full', newdirs)

        self.assertNotIn('listenbrainz-dump-1-20180312-000001-incremental', newdirs)

        self.assertIn('listenbrainz-dump-2-20180312-000002-incremental', newdirs)
        self.assertIn('listenbrainz-dump-3-20180312-000003-incremental', newdirs)
        self.assertIn('listenbrainz-dump-4-20180312-000004-incremental', newdirs)
        self.assertIn('listenbrainz-dump-5-20180312-000005-incremental', newdirs)
        self.assertIn('listenbrainz-dump-6-20180312-000006-incremental', newdirs)
        self.assertIn('listenbrainz-dump-7-20180312-000007-incremental', newdirs)

        self.assertIn('not-a-dump', newdirs)

    def test_create_full_db(self):

        listens = generate_data(1, self.user_name, 1, 5)
        self.listenstore.insert(listens)
        sleep(1)

        # create a full dump
        self.runner.invoke(dump_manager.create_full, ['--location', self.tempdir])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]

        # make sure that the dump contains a full listens dump, a spark dump, a public dump
        # and a private dump
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz'):
                archive_count += 1
        self.assertEqual(archive_count, 4)

        # now, remove the old dump and create a new one with the same id
        shutil.rmtree(os.path.join(self.tempdir, dump_name))
        self.runner.invoke(dump_manager.create_full, ['--location', self.tempdir, '--last-dump-id'])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        recreated_dump_name = os.listdir(self.tempdir)[0]

        # dump names should be the exact same
        self.assertEqual(dump_name, recreated_dump_name)

        # dump should contain the 4 archives
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz'):
                archive_count += 1
        self.assertEqual(archive_count, 4)

    def test_create_full_dump_with_id(self):

        self.listenstore.insert(generate_data(1, self.user_name, 1, 5))
        # if the dump ID does not exist, it should exit with a -1
        result = self.runner.invoke(dump_manager.create_full, ['--location', self.tempdir, '--dump-id', 1000])
        self.assertEqual(result.exit_code, -1)
        self.assertEqual(len(os.listdir(self.tempdir)), 0) # make sure no directory was created either

        # now, add a dump entry to the database and create a dump with that specific dump id
        dump_id = db_dump.add_dump_entry(int(time.time()))
        result = self.runner.invoke(dump_manager.create_full, ['--location', self.tempdir, '--dump-id', dump_id])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]
        created_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(dump_id, created_dump_id)

        # dump should contain the 4 archives
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz'):
                archive_count += 1
        self.assertEqual(archive_count, 4)

    def test_create_incremental(self):
        # create a incremental dump, this won't work because the incremental dump does
        # not have a previous dump
        result = self.runner.invoke(dump_manager.create_incremental, ['--location', self.tempdir])
        self.assertEqual(result.exit_code, -1)
        self.assertEqual(len(os.listdir(self.tempdir)), 0)

        dump_id = db_dump.add_dump_entry(int(time.time()))
        sleep(1)
        self.listenstore.insert(generate_data(1, self.user_name, 1, 5))
        result = self.runner.invoke(dump_manager.create_incremental, ['--location', self.tempdir])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]

        # created dump ID should be one greater than previous dump's ID
        created_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(created_dump_id, dump_id + 1)

        # make sure that the dump contains a full listens dump and a spark dump
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz'):
                archive_count += 1
        self.assertEqual(archive_count, 2)

    def test_create_incremental_dump_with_id(self):

        # if the dump ID does not exist, it should exit with a -1
        result = self.runner.invoke(dump_manager.create_incremental, ['--location', self.tempdir, '--dump-id', 1000])
        self.assertEqual(result.exit_code, -1)

        # create a base dump entry
        t = int(time.time())
        db_dump.add_dump_entry(t)
        sleep(1)
        self.listenstore.insert(generate_data(1, self.user_name, 1, 5))
        sleep(1)

        # create a new dump ID to recreate later
        dump_id = db_dump.add_dump_entry(int(time.time()))
        # now, create a dump with that specific dump id
        result = self.runner.invoke(dump_manager.create_incremental, ['--location', self.tempdir, '--dump-id', dump_id])
        self.assertEqual(len(os.listdir(self.tempdir)), 1)
        dump_name = os.listdir(self.tempdir)[0]
        created_dump_id = int(dump_name.split('-')[2])
        self.assertEqual(dump_id, created_dump_id)

        # dump should contain the spark archive and the listen archive
        archive_count = 0
        for file_name in os.listdir(os.path.join(self.tempdir, dump_name)):
            if file_name.endswith('.tar.xz'):
                archive_count += 1
        self.assertEqual(archive_count, 2)
