import unittest
from unittest.mock import patch
from listenbrainz.listen_writer import ListenWriter

class ListenWriterTestCase(unittest.TestCase):

    def setUp(self):
        self.lwriter = ListenWriter()


    @patch('time.sleep', return_value=None)
    def test_verify_hosts_in_config(self, mock_sleep):
        """ Test for the _verify_hosts_in_config method """

        config1 = self.lwriter.config
        config2 = self.lwriter.config

        if hasattr(config1, "REDIS_HOST"):
            delattr(config1, "REDIS_HOST")

        self.lwriter.config = config1

        with self.assertRaises(SystemExit) as s:
            self.lwriter._verify_hosts_in_config()

        self.assertEqual(s.exception.code, -1)

        if hasattr(config2, "RABBITMQ_HOST"):
            delattr(config2, "RABBITMQ_HOST")

        self.lwriter.config = config2

        with self.assertRaises(SystemExit) as s:
            self.lwriter._verify_hosts_in_config()

        self.assertEqual(s.exception.code, -1)