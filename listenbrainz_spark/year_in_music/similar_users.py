from datetime import date

from listenbrainz_spark.recommendations.recording import create_dataframes
from listenbrainz_spark.user_similarity import user_similarity


def get_similar_users():
    train_model_window = (date.today() - date(2021, 1, 1)).days
    # create_dataframes.main(train_model_window, "similar_users", 50)
    messages = user_similarity.main(25)
    for message in messages:
        yield {
            "type": "similar_users_2021",
            "data": message["data"]
        }
