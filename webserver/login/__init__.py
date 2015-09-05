from flask import redirect, url_for
from flask_login import LoginManager, UserMixin, current_user
from functools import wraps
import db.user

login_manager = LoginManager()
login_manager.login_view = 'login.index'


class User(UserMixin):
    def __init__(self, id, created, musicbrainz_id):
        self.id = id
        self.created = created
        self.musicbrainz_id = musicbrainz_id


@login_manager.user_loader
def load_user(user_id):
    user = db.user.get(user_id)
    if user:
        return User(
            id=user['id'],
            created=user['created'],
            musicbrainz_id=user['musicbrainz_id'],
        )
    else:
        return None


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_anonymous() is False:
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)

    return decorated
