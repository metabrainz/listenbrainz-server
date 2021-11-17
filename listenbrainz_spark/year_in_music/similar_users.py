from datetime import date

from listenbrainz_spark.recommendations.recording import create_dataframes
from listenbrainz_spark.user_similarity import user_similarity


def get_similar_users():
    train_model_window = (date.today() - date(2021, 1, 1)).days
    create_dataframes.main(train_model_window, "similar_users", 50)
    similar_users_df = user_similarity.get_similar_users_df(25)

    itr = similar_users_df.toLocalIterator()
    message = {
        row.user_name: {
            user.other_user_name: user.similarity
            for user in row.similar_users
        }
        for row in itr
    }

    yield {
        "type": "similar_users_2021",
        "data": message
    }
