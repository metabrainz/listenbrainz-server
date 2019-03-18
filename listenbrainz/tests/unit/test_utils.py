# listenbrainz-server - Server for the ListenBrainz project.
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

import listenbrainz.utils as utils
import pika
import time
import unittest
import uuid

from datetime import datetime
from listenbrainz.webserver import create_app
from listenbrainz.webserver.views.api_tools import is_valid_uuid

class ListenBrainzUtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(debug=True) # create an app for config value access

    def test_create_channel_to_consume(self):
        connection = utils.connect_to_rabbitmq(
            username=self.app.config['RABBITMQ_USERNAME'],
            password=self.app.config['RABBITMQ_PASSWORD'],
            host=self.app.config['RABBITMQ_HOST'],
            port=self.app.config['RABBITMQ_PORT'],
            virtual_host=self.app.config['RABBITMQ_VHOST'],
            error_logger=print,
        )

        ch = utils.create_channel_to_consume(
            connection=connection,
            exchange='test',
            queue='test',
            callback_function=lambda a, b, c, d: None
        )
        self.assertIsNotNone(ch)
        self.assertIsInstance(ch, pika.adapters.blocking_connection.BlockingChannel)

    def test_unix_timestamp_to_datetime(self):
        t = int(time.time())
        x = utils.unix_timestamp_to_datetime(t)
        self.assertIsInstance(x, datetime)
        self.assertEqual(int(x.strftime('%s')), t)

    def test_valid_uuid(self):
        self.assertTrue(is_valid_uuid(str(uuid.uuid4())))
        self.assertFalse(is_valid_uuid('hjjkghjk'))
        self.assertFalse(is_valid_uuid(123))
