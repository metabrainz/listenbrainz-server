import uuid
import logging

from datetime import datetime
import listenbrainz_spark.utils.mapping as mapping_utils
from listenbrainz_spark.stats import (replace_days,
                                      offset_days)
from listenbrainz_spark.utils import get_latest_listen_ts
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
