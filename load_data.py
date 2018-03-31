def load_listenbrainz_dump():
    """ Returns an RDD of format (user_name, track_name, release_name, timestamp, additional_info)
    """
    raise NotImplementedError


def prepare_user_data():
    """ Returns an RDD that is of the form (user_id, user_name)
    """
    raise NotImplementedError


def prepare_recording_data():
    """ Returns an RDD of the form (recording_id, recording_name)
    """
    raise NotImplementedError


def prepare_listen_counts():
    """ calculates ratings, returns rdd of the form (user_id, recording_id, play_count)
    """
    raise NotImplementedError

def get_listen_counts_for_user(user_id):
    """ returns rdd for a user's recording play counts
    (user_id = specified user id, recording_id, play_count)
    """
    raise NotImplementedError
