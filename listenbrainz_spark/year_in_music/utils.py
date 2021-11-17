from datetime import datetime

from listenbrainz_spark.utils import get_listens_from_new_dump


def setup_2021_listens():
    start = datetime(2021, 1, 1, 0, 0, 0)
    end = datetime.now()
    listens = get_listens_from_new_dump(start, end)
    listens.createOrReplaceTempView("listens_2021")
