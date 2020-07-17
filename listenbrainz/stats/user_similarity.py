import json
from listenbrainz.db.stats import get_artists_for_all_users
import listenbrainz.db.user as db_user
from scipy.sparse import csr_matrix
import implicit


def get_artist_user_matrix(user_artist_stats):
    """ Returns a Scipy sparse matrix with artists as rows, users as column
    and the listen count as the value. This is then used to train the CF model.
    """
    artist_ids = {}
    count = 0
    data = []
    row_ind = []
    col_ind = []
    for stat_record in user_artist_stats:
        for artist in stat_record.all_time.artists:
            if artist.artist_name in artist_ids: #TODO: use artist MSID or MBID
                continue
            else:
                artist_ids[artist.artist_name] = count
                count += 1
                data.append(artist.listen_count)
                row_ind.append(artist_ids[artist.artist_name])
                col_ind.append(stat_record.user_id)
    return csr_matrix((data, (row_ind, col_ind)), dtype=int)


def calculate_similar_users():
    print("Getting stats from the database...")
    user_artist_stats = get_artists_for_all_users()
    print("Done!")

    print("Constructing artist-user matrix...")
    csr_matrix = get_artist_user_matrix(user_artist_stats)
    print("Done!")

    print("Training model...")
    model = implicit.als.AlternatingLeastSquares(factors=50)
    model.fit(csr_matrix)
    print("Done!")

    for stat_record in user_artist_stats:
        print("Generating similar users to user ID: %d" % stat_record.user_id)
        similar_users = model.similar_users(stat_record.user_id, N=50)
        db_user.insert_similar_users(stat_record.user_id, similar_users)
        print("Done!")
