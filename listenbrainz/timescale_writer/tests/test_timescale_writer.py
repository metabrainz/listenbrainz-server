import unittest
from unittest.mock import patch

from listenbrainz.timescale_writer.timescale_writer import TimescaleWriterSubscriber
from listenbrainz.webserver import create_app


class TimescaleWriterTestCase(unittest.TestCase):

    def setUp(self):
        self.lwriter = TimescaleWriterSubscriber()

    @patch('time.sleep', return_value=None)
    def test_verify_hosts_in_config(self, mock_sleep):
        """ Test for the _verify_hosts_in_config method """

        app1 = create_app()
        app2 = create_app()

        if "REDIS_HOST" in app1.config:
            app1.config.pop("REDIS_HOST")

        with self.assertRaises(SystemExit) as s:
            with app1.app_context():
                self.lwriter._verify_hosts_in_config()
                self.assertEqual(s.exception.code, -1)

        if "RABBITMQ_HOST" in app2.config:
            app2.config.pop("RABBITMQ_HOST")

        with self.assertRaises(SystemExit) as s:
            with app2.app_context():
                self.lwriter._verify_hosts_in_config()
                self.assertEqual(s.exception.code, -1)
