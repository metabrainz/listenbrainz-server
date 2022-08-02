# messybrainz-server - Server for the MessyBrainz project
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import unittest
from listenbrainz import messybrainz as msb
from listenbrainz import config

ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'admin', 'messybrainz', 'sql')


class MessyBrainzTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        msb.init_db_connection(config.MESSYBRAINZ_SQLALCHEMY_DATABASE_URI)

    def setUp(self):
        self.msb_conn = msb.engine.connect()
        self.msb_trans = self.msb_conn.begin()

    def tearDown(self):
        self.msb_trans.rollback()
        self.msb_conn.close()
