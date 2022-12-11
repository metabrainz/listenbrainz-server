from datetime import date, datetime, time

from listenbrainz_spark.recommendations.recording.create_dataframes import calculate_dataframes
from listenbrainz_spark.similarity.user import get_similar_users_df


def get_similar_users(year):
    from_date = datetime(year, 1, 1)
    to_date = datetime.combine(date(year, 12, 31), time.max)
    calculate_dataframes(from_date, to_date, "similar_users", 50)
    similar_users_df = get_similar_users_df(25)

    itr = similar_users_df.toLocalIterator()
    message = {
        row.user_id: {
            user.other_user_id: user.similarity
            for user in row.similar_users
        }
        for row in itr
    }

    yield {
        "type": "year_in_music_similar_users",
        "year": year,
        "data": message
    }
