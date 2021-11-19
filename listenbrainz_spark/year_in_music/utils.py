from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.utils import get_listens_from_new_dump


def setup_2021_listens():
    start = datetime(2021, 1, 1, 0, 0, 0)
    end = datetime.now()
    listens = get_listens_from_new_dump(start, end)
    listens.createOrReplaceTempView("listens_2021")


def setup_all_releases():
    listenbrainz_spark\
        .sql_context\
        .read\
        .json(path.MUSICBRAINZ_RELEASE_DUMP_JSON_FILE)\
        .createOrReplaceTempView("release")
