from listenbrainz.db import user as db_user


def pause_user(db_conn,user_id):
    """ Pause a user from ListenBrainz. First, changes the is_paused flag 
    to true and then sends them an e-mail. 

    Args:
        user_id: the LB row ID of the user
    """
    db_user.pause(db_conn,user_id)
    db_conn.commit()


def unpause_user(db_conn,user_id):
    """ Unpause a user from ListenBrainz. First, changes the is_paused flag 
    to false and then sends them an e-mail. 

    Args:
        user_id: the LB row ID of the user
    """
    db_user.unpause(db_conn,user_id)
    db_conn.commit()