from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark import utils, path
import listenbrainz_spark.utils.mapping as mapping_utils

from pyspark.sql import Row


class MappingUtilsTestCase(SparkTestCase):
    mapping_path = path.MBID_MSID_MAPPING

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_test_mapping_to_hdfs(cls.mapping_path)

    def test_get_unique_rows_from_mapping(self):
        df = utils.read_files_from_HDFS(self.mapping_path)
        mapping_df = mapping_utils.get_unique_rows_from_mapping(df)

        self.assertEqual(mapping_df.count(), 3)
        cols = [
            'mb_artist_credit_id',
            'mb_artist_credit_mbids',
            'mb_artist_credit_name',
            'mb_recording_mbid',
            'mb_recording_name',
            'mb_release_mbid',
            'mb_release_name',
            'msb_artist_credit_name_matchable',
            'msb_recording_name_matchable'
        ]
        self.assertEqual(sorted(mapping_df.columns), sorted(cols))

    def test_unaccent_artist_and_track_name(self):
        df = utils.create_dataframe(
            Row(
                artist_name='égè,câ,î or ô)tñü or ï(ç)',
                track_name='égè,câ,î or ô)tñü lalaor ïïï(ç)'
            ),
            schema=None
        )

        res_df = mapping_utils.unaccent_artist_and_track_name(df)
        self.assertEqual(res_df.collect()[0].unaccented_artist_name, 'ege,ca,i or o)tnu or i(c)')
        self.assertEqual(res_df.collect()[0].unaccented_track_name, 'ege,ca,i or o)tnu lalaor iii(c)')

    def test_convert_text_fields_to_matchable(self):
        df = utils.create_dataframe(
            Row(
                artist_name='égè,câ,î or ô)tñü or ï(ç)  !"#$%&\'()*+, L   ABD don''t-./:;<=>?@[]^_`{|}~',
                track_name='égè,câ,î or ô)tñü lalaor ïïï(ç)!"#$%&\'()*+, L       ABD don''t lie-./:;<=>?@[]^_`{|}~'
            ),
            schema=None
        )

        res_df = mapping_utils.convert_text_fields_to_matchable(df)
        res_df.show()
        self.assertEqual(res_df.collect()[0].artist_name_matchable, 'egecaiorotnuoriclabddont')
        self.assertEqual(res_df.collect()[0].track_name_matchable, 'egecaiorotnulalaoriiiclabddontlie')
