import os
import json
import tarfile
import tempfile
import subprocess
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from listenbrainz_spark import config, utils, schema
from listenbrainz_spark.exceptions import DumpInvalidException
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader


test_listen = {

            'user_name': 'vansika',
            'artist_msid': "a36d6fc9-49d0-4789-a7dd-a2b72369ca45",
            'release_msid' : "xxxxxx",
            'release_name': "xxxxxx",
            'artist_name': "Less Than Jake",
            'release_mbid': "xxxxxx",
            'track_name': "Al's War",
            'recording_msid': "cb6985cd-cc71-4d59-b4fb-2e72796af741",
            'tags': ['xxxx'],
            'listened_at': str(datetime.utcnow())
        }


class HDFSTestCase(unittest.TestCase):

    @patch('listenbrainz_spark.hdfs_connection.init_hdfs')
    @patch('listenbrainz_spark.init_spark_session')
    def test_init(self, mock_spark_init, mock_hdfs_init):
        ListenbrainzHDFSUploader()
        mock_hdfs_init.assert_called_once_with(config.HDFS_HTTP_URI)
        mock_spark_init.assert_called_once()

    def test_is_json_file(self):
        self.assertTrue(ListenbrainzHDFSUploader()._is_json_file('file.json'))
        self.assertFalse(ListenbrainzHDFSUploader()._is_json_file('file.txt'))

    @patch('listenbrainz_spark.hdfs.subprocess.Popen')
    def test_get_pxz_output(self, mock_popen):
        pxz = ListenbrainzHDFSUploader().get_pxz_output('faketar', threads=8)
        mock_popen.assert_called_once()
        self.assertEqual(pxz, mock_popen.return_value)

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
            pxz_command = ['pxz', '--compress']
            pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:
                json_file_path = os.path.join(temp_dir, '1.json')
                with open(json_file_path, 'w') as f:
                    json.dump(test_listen, f)
                tar.add(json_file_path, arcname=os.path.join('temp_tar', '2020', '1.json'))

                invalid_json_file_path = os.path.join(temp_dir, 'invalid.txt')
                with open(invalid_json_file_path, 'w') as f:
                    f.write('test file')
                tar.add(invalid_json_file_path, arcname=os.path.join('temp_tar', 'invalid.txt'))
            pxz.stdin.close()

        pxz.wait()
        return temp_archive

    def test_upload_archive(self):
        archive_path = self.create_test_tar()
        pxz = ListenbrainzHDFSUploader().get_pxz_output(archive_path)
        tmp_dump_dir = tempfile.mkdtemp()

        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            ListenbrainzHDFSUploader().upload_archive(tmp_dump_dir, tar, '/test', schema.listen_schema,
                                                      ListenbrainzDataUploader().process_json_listens)

        walk = utils.hdfs_walk('/test', depth=1)
        dirs = next(walk)[1]
        self.assertEqual(len(dirs), 1)

        df = utils.read_files_from_HDFS('/test/2020/1.parquet')
        self.assertEqual(df.count(), 1)

        status = utils.path_exists(tmp_dump_dir)
        self.assertFalse(status)

        utils.delete_dir('/test', recursive=True)

    def test_upload_archive_failed(self):
        faulty_tar = MagicMock()
        faulty_tar.extract.side_effect = tarfile.ReadError()
        member = MagicMock()
        faulty_tar.__iter__.return_value = [member]

        tmp_dump_dir = tempfile.mkdtemp()
        self.assertRaises(DumpInvalidException, ListenbrainzHDFSUploader().upload_archive, tmp_dump_dir,
                          faulty_tar, '/test', schema.listen_schema, ListenbrainzDataUploader().process_json_listens)

        status = utils.path_exists('/test')
        self.assertFalse(status)
