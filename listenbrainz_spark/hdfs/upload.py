import os
import time
import tarfile

import listenbrainz_spark
from listenbrainz_spark import schema, path, config, utils
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader

from flask import current_app

class ListenbrainzDataUploader(ListenbrainzHDFSUploader):

    def process_json_mapping(self, _, dest_path, tmp_hdfs_path):
        """ Read mapping JSON from HDFS as a dataframe and upload to
            HDFS as a parquet.

            Args:
                dest_path (str): HDFS path to upload mappping as parquet.
                tmp_hdfs_path (str): HDFS path where mapping JSON has been uploaded.
        """
        df = utils.read_json(tmp_hdfs_path, schema=schema.mapping_schema)
        utils.save_parquet(df, dest_path)
        df = utils.read_files_from_HDFS(dest_path)
        df.show()
        print(df.count())
        df.printSchema()

    def process_json_listens(self, filename, data_dir, tmp_hdfs_path):
        """ Process a file containing listens from the ListenBrainz dump and add listens to
            appropriate dataframes.

            Args:
                filename (str): File name of JSON file.
                data_dir (str): Dir to save listens to in HDFS as parquet.
                tmp_HDFS_path (str): HDFS path where listens JSON has been uploaded.
        """
        start_time = time.time()
        df = utils.read_json(tmp_hdfs_path, schema=schema.listen_schema).cache()
        current_app.logger.info("Processing {} listens...".format(df.count()))

        if filename.split('/')[-1] == 'invalid.json':
            dest_path = os.path.join(data_dir, 'invalid.parquet')
        else:
            year = filename.split('/')[-2]
            month = filename.split('/')[-1][0:-5]
            dest_path = os.path.join(data_dir, year, '{}.parquet'.format(str(month)))

        current_app.logger.info("Uploading to {}...".format(dest_path))
        utils.save_parquet(df, dest_path)
        current_app.logger.info("File processed in {:.2f} seconds!".format(time.time() - start_time))

        df = utils.read_files_from_HDFS(dest_path)
        df.show()
        print(df.count())
        df.printSchema()

    def upload_mapping(self, archive):
        """ Decompress archive and upload mapping to HDFS.

            Args:
                archive: Mapping tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            self.upload_archive(tar, path.RECORDING_ARTIST_MBID_MSID_MAPPING, self.process_json_mapping)

    def upload_listens(self, archive):
        """ Decompress archive and upload listens to HDFS.

            Args:
                archive: listens tar file to upload.
        """
        pxz = self.get_pxz_output(archive)
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            self.upload_archive(tar, path.LISTENBRAINZ_DATA_DIRECTORY, self.process_json_listens)
