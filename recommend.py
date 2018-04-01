from setup import spark, sc
import utils
from pyspark.mllib.recommendation import MatrixFactorizationModel
import sys


def load_model(path):
    return MatrixFactorizationModel.load(sc, path)


def get_user_id(user_name):
    result = spark.sql("""
        SELECT user_id
          FROM user
         WHERE user_name = '%s'
    """ % user_name)
    return result.first()['user_id']


def recommend_user(user_name, model, recordings_map):
    user_id = get_user_id(user_name)
    user_playcounts = spark.sql("""
        SELECT user_id,
               recording_id,
               count
          FROM playcount
         WHERE user_id = %d
    """ % user_id)

    user_recordings = user_playcounts.rdd.map(lambda r: r['recording_id'])
    all_recordings =  recordings_map.keys()
    candidate_recordings = all_recordings.subtract(user_recordings)
    recommendations = model.predictAll(candidate_recordings.map(lambda recording: (user_id, recording))).takeOrdered(10, lambda product: -product.rating)

    recommended_recordings = [recordings_map.lookup(recommendations[i].product) for i in range(len(recommendations))]
    return recommended_recordings


def main():
    if len(sys.argv) < 4:
        print("Usage: python recommend.py [table_dir] [models_dir] [user_name]")
        sys.exit(0)

    table_dir = sys.argv[1]
    models_dir = sys.argv[2]
    user_name = sys.argv[3]

    users_df = utils.load_users_df(table_dir)
    users_df.createOrReplaceTempView('user')
    playcounts_df = utils.load_playcounts_df(table_dir)
    playcounts_df.createOrReplaceTempView('playcount')
    recordings_df = utils.load_recordings_df(table_dir)
    recordings_map = recordings_df.rdd.map(lambda r: (r['recording_id'], (r['track_name'], r['recording_msid'])))
    model = load_model(models_dir)
    print(recommend_user(user_name, model, recordings_map))


if __name__ == '__main__':
    main()
