import uuid
import logging

import listenbrainz_spark.utils.mapping as mapping_utils
from listenbrainz_spark.stats import (replace_days,
                                      offset_days)
from listenbrainz_spark.stats.utils import get_latest_listen_ts
from listenbrainz_spark.utils import save_parquet, get_listens
from listenbrainz_spark.exceptions import (FileNotSavedException,
                                           FileNotFetchedException)


logger = logging.getLogger(__name__)


def get_dataframe_id(prefix):
    """ Generate dataframe id.
    """
    return '{}-{}'.format(prefix, uuid.uuid4())


def save_dataframe(df, dest_path):
    """ Save dataframe to HDFS.

        Args:
            df : Dataframe to save.
            dest_path (str): HDFS path to save dataframe.
    """
    try:
        save_parquet(df, dest_path)
    except FileNotSavedException as err:
        logger.error(str(err), exc_info=True)
        raise


def get_dates_to_train_data(train_model_window):
    """ Get window to fetch listens to train data.

        Args:
            train_model_window (int): model to be trained on data of given number of days.

        Returns:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
    """
    to_date = get_latest_listen_ts()
    from_date = offset_days(to_date, train_model_window)
    # shift to the first of the month
    from_date = replace_days(from_date, 1)
    return to_date, from_date


def get_mapped_artist_and_recording_mbids(partial_listens_df, msid_mbid_mapping_df):
    """ Map recording msid->mbid and artist msid->mbids so that every listen has an mbid.

        Args:
            partial_listens_df (dataframe): listens without artist mbid and recording mbid.
            msid_mbid_mapping_df (dataframe): msid->mbid mapping. For columns refer to
                                              msid_mbid_mapping_schema in listenbrainz_spark/schema.py
        Returns:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.
    """
    condition = [
        partial_listens_df.track_name_matchable == msid_mbid_mapping_df.msb_recording_name_matchable,
        partial_listens_df.artist_name_matchable == msid_mbid_mapping_df.msb_artist_credit_name_matchable
    ]

    df = partial_listens_df.join(msid_mbid_mapping_df, condition, 'inner')
    # msb_release_name_matchable is skipped till the bug in mapping is resolved.
    # bug : release_name in listens and mb_release_name in mapping is different.
    mapped_listens_df = df.select('listened_at',
                                  'mb_artist_credit_id',
                                  'mb_artist_credit_mbids',
                                  'mb_recording_mbid',
                                  'mb_release_mbid',
                                  'msb_artist_credit_name_matchable',
                                  'msb_recording_name_matchable',
                                  'user_name')

    return mapped_listens_df


def get_listens_for_training_model_window(to_date, from_date, dest_path):
    """  Prepare dataframe of listens to train.

        Args:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
            dest_path (str): HDFS path.

        Returns:
            partial_listens_df (dataframe): dataframe of listens.
    """
    try:
        training_df = get_listens(from_date, to_date, dest_path)
    except ValueError as err:
        logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        logger.error(str(err), exc_info=True)
        raise

    partial_listens_df = mapping_utils.convert_text_fields_to_matchable(training_df)
    return partial_listens_df
