import os
import time
import tarfile
import tempfile
import logging

from listenbrainz_spark import schema, path, utils
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader


logger = logging.getLogger(__name__)


class ListenbrainzDataUploader(ListenbrainzHDFSUploader):

    def process_json(self, _, dest_path, tmp_hdfs_path, __, schema):
        """ Read JSON from HDFS as a dataframe and upload to
            HDFS as a parquet.

            Args:
                dest_path (str): HDFS path to upload JSON as parquet.
                tmp_hdfs_path (str): HDFS path where JSON has been uploaded.
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)
        logger.info("Processing {} rows...".format(df.count()))

        logger.info("Uploading to {}...".format(dest_path))
        utils.save_parquet(df, dest_path)
        logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def process_json_listens(self, filename, data_dir, tmp_hdfs_path, append, schema):
        """ Process a file containing listens from the ListenBrainz dump and add listens to
            appropriate dataframes.

            Args:
                filename (str): File name of JSON file.
                data_dir (str): Dir to save listens to in HDFS as parquet.
                tmp_hdfs_path (str): HDFS path where listens JSON has been uploaded.
                append (bool): If true append to end of parquet rather than write.
                schema: Schema of the listens
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)

        if filename.split('/')[-1] == 'invalid.json':
            dest_path = os.path.join(data_dir, 'invalid.parquet')
        else:
            year = filename.split('/')[-2]
            month = filename.split('/')[-1][0:-5]
            dest_path = os.path.join(data_dir, year, '{}.parquet'.format(str(month)))

        if append and utils.path_exists(dest_path):
            utils.save_parquet(df, dest_path, mode="append")
        else:
            utils.save_parquet(df, dest_path, mode="overwrite")

        logger.info("Uploading to {}...".format(dest_path))
        logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def upload_mapping(self, archive: str):
        """ Decompress archive and upload mapping to HDFS.

            Args:
                archive: Mapping tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.MBID_MSID_MAPPING, schema.msid_mbid_mapping_schema,
                                    self.process_json, overwrite=True)

    def upload_listens(self, archive: str, overwrite: bool = False):
        """ Decompress archive and upload listens to HDFS.

            Args:
                archive: Listens tar file to upload.
                overwrite: If True, overwrites the previously present listens,
                           if False merges the previously present listens with the new ones.
        """
        pxz = self.get_pxz_output(archive)
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.LISTENBRAINZ_DATA_DIRECTORY, schema.listen_schema,
                                    self.process_json_listens, overwrite=overwrite)

    def upload_artist_relation(self, archive: str):
        """ Decompress archive and upload artist relation to HDFS.

            Args:
                archive: artist relation tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema,
                                    self.process_json, overwrite=True)
