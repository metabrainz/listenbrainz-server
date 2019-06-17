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

import listenbrainz.db.dump_manager as dump_manager
import os
import unittest
import tempfile

from listenbrainz.utils import create_path

class DumpManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()


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
