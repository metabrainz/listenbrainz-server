from flask import redirect, url_for, current_app, request
from flask_login import LoginManager, UserMixin, current_user
from functools import wraps
import listenbrainz.db.user as db_user

login_manager = LoginManager()
login_manager.login_view = 'login.index'


class User(UserMixin):
    def __init__(self, id, created, musicbrainz_id, auth_token, gdpr_agreed):
        self.id = id
        self.created = created
        self.musicbrainz_id = musicbrainz_id
        self.auth_token = auth_token
        self.gdpr_agreed = gdpr_agreed

    @classmethod
    def from_dbrow(cls, user):
        return cls(
            id=user['id'],
            created=user['created'],
            musicbrainz_id=user['musicbrainz_id'],
            auth_token=user['auth_token'],
            gdpr_agreed=user['gdpr_agreed'],
        )

@login_manager.user_loader
def load_user(user_id):
    user = db_user.get(user_id)
    if user:
        return User.from_dbrow(user)
    else:
        return None


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_anonymous:
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)

    return decorated
