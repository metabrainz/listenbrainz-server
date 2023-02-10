from datetime import datetime, date, time

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.utils import get_listens_from_dump


def setup_listens_for_year(year):
    start = datetime(year, 1, 1)
    end = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_dump(start, end)
    listens.createOrReplaceTempView("listens_of_year")


def setup_all_releases():
    listenbrainz_spark\
        .sql_context\
        .read\
        .json(path.MUSICBRAINZ_RELEASE_DUMP_JSON_FILE)\
        .createOrReplaceTempView("release")
