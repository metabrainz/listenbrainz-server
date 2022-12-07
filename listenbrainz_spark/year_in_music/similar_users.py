from datetime import date, datetime, time

from listenbrainz_spark.recommendations.recording.create_dataframes import calculate_dataframes
from listenbrainz_spark.similarity import user


def get_similar_users(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    calculate_dataframes(from_date, to_date, "similar_users", 50)
    similar_users_df = user_similarity.get_similar_users_df(25)

    itr = similar_users_df.toLocalIterator()
    message = {
        row.user_id: {
            user.other_user_name: user.similarity
            for user in row.similar_users
        }
        for row in itr
    }

    yield {
        "type": "similar_users_year_end",
        "data": message
    }
