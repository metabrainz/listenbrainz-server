import unidecode
from pyspark.sql.functions import lower, regexp_replace, udf
from pyspark.sql.types import StringType


def get_unique_rows_from_mapping(df):
    """ Get unique rows from the mapping.
    """
    msid_mbid_mapping_df = df.select('mb_artist_credit_id',
                                     'mb_artist_credit_mbids',
                                     'mb_artist_credit_name',
                                     'mb_recording_mbid',
                                     'mb_recording_name',
                                     'mb_release_mbid',
                                     'mb_release_name',
                                     'msb_artist_credit_name_matchable',
                                     'msb_recording_name_matchable') \
        .distinct()

    return msid_mbid_mapping_df


def unaccent_artist_and_track_name(df):
    """ Remove accents from artist and track name.

        Args:
            df: Dataframe to process.

        Returns:
            res_df: Dataframe with unaccented artist name and track name.
    """

    def get_unaccented_string(accented_string):
        return unidecode.unidecode(accented_string)

    unaccent_udf = udf(get_unaccented_string, StringType())

    intermediate_df = df.withColumn("unaccented_artist_name", unaccent_udf(df.artist_name))

    res_df = intermediate_df.withColumn("unaccented_track_name", unaccent_udf(intermediate_df.track_name))

    return res_df


def convert_text_fields_to_matchable(df):
    """ Convert text fields (names i.e artist_name, track_name etc) to matchable field.
        The following steps convert a text field to a matchable field:
            1.  Unaccent the text.
            2.  Remove punctuations and whitespaces.
            3.  Convert to lowercase.

        Args:
            df: Dataframe to process

        Returns:
            res_df: Dataframe with artist_name and track_name converted to matchable fields.
    """
    unaccent_df = unaccent_artist_and_track_name(df)

    intermediate_df = unaccent_df.withColumn(
        "artist_name_matchable",
        lower(regexp_replace("unaccented_artist_name", '[^A-Za-z0-9]+', ""))
    )

    res_df = intermediate_df.withColumn(
        "track_name_matchable",
        lower(regexp_replace("unaccented_track_name", '[^A-Za-z0-9]+', ""))
    )

    return res_df
