import os
import time
import tarfile
import tempfile

import listenbrainz_spark
from listenbrainz_spark import schema, path, config, utils
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader

from flask import current_app


class ListenbrainzDataUploader(ListenbrainzHDFSUploader):

    def process_json(self, _, dest_path, tmp_hdfs_path, schema):
        """ Read JSON from HDFS as a dataframe and upload to
            HDFS as a parquet.

            Args:
                dest_path (str): HDFS path to upload JSON as parquet.
                tmp_hdfs_path (str): HDFS path where JSON has been uploaded.
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)
        current_app.logger.info("Processing {} rows...".format(df.count()))

        current_app.logger.info("Uploading to {}...".format(dest_path))
        utils.save_parquet(df, dest_path)
        current_app.logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def process_json_listens(self, filename, data_dir, tmp_hdfs_path, schema):
        """ Process a file containing listens from the ListenBrainz dump and add listens to
            appropriate dataframes.

            Args:
                filename (str): File name of JSON file.
                data_dir (str): Dir to save listens to in HDFS as parquet.
                tmp_hdfs_path (str): HDFS path where listens JSON has been uploaded.
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)

        if filename.split('/')[-1] == 'invalid.json':
            dest_path = os.path.join(data_dir, 'invalid.parquet')
        else:
            year = filename.split('/')[-2]
            month = filename.split('/')[-1][0:-5]
            dest_path = os.path.join(data_dir, year, '{}.parquet'.format(str(month)))

        if utils.path_exists(dest_path):
            df.write.mode('append').parquet(dest_path)
        else:
            utils.save_parquet(df, dest_path)

        current_app.logger.info("Uploading to {}...".format(dest_path))
        current_app.logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def upload_mapping(self, archive):
        """ Decompress archive and upload mapping to HDFS.

            Args:
                archive: Mapping tar file to upload.
                force: If True deletes dir at path where mappings are to be uploaded.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.MBID_MSID_MAPPING, schema.msid_mbid_mapping_schema,
                                    self.process_json, force=True)

    def upload_listens(self, archive, force=False):
        """ Decompress archive and upload listens to HDFS.

            Args:
                archive: listens tar file to upload.
                force: If True deletes dir at path where listens are to be uploaded,
                       if False merges the previously present listens with the new ones.
        """
        pxz = self.get_pxz_output(archive)
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.LISTENBRAINZ_DATA_DIRECTORY, schema.listen_schema,
                                    self.process_json_listens, force=force)

    def upload_artist_relation(self, archive):
        """ Decompress archive and upload artist relation to HDFS.

            Args:
                archive: artist relation tar file to upload.
                force: If True deletes dir at path where artist relations are to be uploaded.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema,
                                    self.process_json, force=True)
