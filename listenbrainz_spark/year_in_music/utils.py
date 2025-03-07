from datetime import datetime, date, time

from listenbrainz_spark.listens.data import get_listens_from_dump


def setup_listens_for_year(year):
    start = datetime(year, 1, 1)
    end = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_dump(start, end)
    listens.createOrReplaceTempView("listens_of_year")
