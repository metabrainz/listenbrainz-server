import uuid
import logging

from datetime import datetime
from listenbrainz_spark.stats import (replace_days,
                                      offset_days)
from listenbrainz_spark.listens.data import get_latest_listen_ts
from listenbrainz_spark.utils import save_parquet
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
