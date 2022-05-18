import os
import json
import tarfile
import tempfile
import subprocess
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

import logging

from listenbrainz_spark import config, utils, schema
from listenbrainz_spark.exceptions import DumpInvalidException
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.tests import SparkNewTestCase


class HDFSTestCase(SparkNewTestCase):

    def test_is_json_file(self):
        self.assertTrue(ListenbrainzHDFSUploader()._is_json_file('file.json'))
        self.assertFalse(ListenbrainzHDFSUploader()._is_json_file('file.txt'))

    @patch('listenbrainz_spark.hdfs.subprocess.Popen')
    def test_get_xz_output(self, mock_popen):
        xz = ListenbrainzHDFSUploader().get_xz_output('faketar', threads=8)
        mock_popen.assert_called_once()
        self.assertEqual(xz, mock_popen.return_value)

    def create_test_tar(self):
        """ Creates a tar file to test listenbrainz_spark.hdfs.ListenbrainzHDFSUploader.upload_archive

            Note:
                Motive of the test is to check the fashion in which upload_archive unfolds.
                It would behave the same for mappings, artist_relation and listens.
                Here, the tar has been created solely for listens, if you wish to check for mappings or artist_relation
                change the tar file member names, types, schema, callback etc accordingly.
        """
        temp_archive = os.path.join(tempfile.mkdtemp(), 'temp_tar.tar.xz')
        temp_dir = tempfile.mkdtemp()
        with open(temp_archive, 'w') as archive:
            xz_command = ['xz', '--compress']
            xz = subprocess.Popen(xz_command, stdin=subprocess.PIPE, stdout=archive)
            test_entry = {
                "id_1": 11285,
                "name_1": "Wolfgang Amadeus Mozart",
                "name_0": "Ludwig van Beethoven",
                "id_0": 1021,
                "score": 1.0
            }

            with tarfile.open(fileobj=xz.stdin, mode='w|') as tar:
                json_file_path = os.path.join(temp_dir, 'artist_credit-artist_credit-relations.json')
                with open(json_file_path, 'w') as f:
                    json.dump(test_entry, f)
                tar.add(json_file_path, arcname=os.path.join('mbdump', 'artist_credit-artist_credit-relations.json'))

                invalid_json_file_path = os.path.join(temp_dir, 'invalid.txt')
                with open(invalid_json_file_path, 'w') as f:
                    f.write('test file')
                tar.add(invalid_json_file_path, arcname=os.path.join('temp_tar', 'invalid.txt'))
            xz.stdin.close()

        xz.wait()
        return temp_archive

    def test_upload_archive(self):
        archive_path = self.create_test_tar()
        xz = self.uploader.get_xz_output(archive_path)
        tmp_dump_dir = tempfile.mkdtemp()

        with tarfile.open(fileobj=xz.stdout, mode='r|') as tar:
            self.uploader.upload_archive(tmp_dump_dir, tar, '/artist_relations.parquet',
                                         schema.artist_relation_schema, self.uploader.process_json)

        df = utils.read_files_from_HDFS('/artist_relations.parquet')
        self.assertEqual(df.count(), 1)

        status = utils.path_exists(tmp_dump_dir)
        self.assertFalse(status)

        utils.delete_dir('/artist_relations.parquet', recursive=True)

    def test_upload_archive_failed(self):
        faulty_tar = MagicMock()
        faulty_tar.extract.side_effect = tarfile.ReadError()
        member = MagicMock()
        faulty_tar.__iter__.return_value = [member]

        tmp_dump_dir = tempfile.mkdtemp()
        self.assertRaises(DumpInvalidException, self.uploader.upload_archive, tmp_dump_dir,
                          faulty_tar, '/test', schema.artist_relation_schema, self.uploader.process_json)

        status = utils.path_exists('/test')
        self.assertFalse(status)
