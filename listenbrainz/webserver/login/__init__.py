from flask import redirect, url_for, current_app, request
from flask_login import LoginManager, UserMixin, current_user
from functools import wraps
import listenbrainz.db.user as db_user
from werkzeug.exceptions import Unauthorized

from listenbrainz.webserver import db_conn
from listenbrainz.webserver.errors import APIUnauthorized

login_manager = LoginManager()
login_manager.login_view = 'login.index'


class User(UserMixin):
    def __init__(self, id, created, musicbrainz_id, auth_token, gdpr_agreed, login_id):
        self.id = id
        self.created = created
        self.musicbrainz_id = musicbrainz_id
        self.auth_token = auth_token
        self.gdpr_agreed = gdpr_agreed
        self.login_id = login_id

    def get_id(self):
        return self.login_id

    @classmethod
    def from_dbrow(cls, user):
        return cls(
            id=user['id'],
            created=user['created'],
            musicbrainz_id=user['musicbrainz_id'],
            auth_token=user['auth_token'],
            gdpr_agreed=user['gdpr_agreed'],
            login_id=user['login_id'],
        )

    def to_dict(self):
        return {
            "id": self.id,
            "created": self.created,
            "musicbrainz_id": self.musicbrainz_id,
            "auth_token": self.auth_token,
            "gdpr_agreed": self.gdpr_agreed,
            "login_id": self.login_id
        }


@login_manager.user_loader
def load_user(user_login_id):
    try:
        user = db_user.get_by_login_id(db_conn, user_login_id)
    except Exception as e:
        db_conn.rollback()
        current_app.logger.error("Error while getting user by login ID: %s", str(e), exc_info=True)
        return None
    if user:
        return User.from_dbrow(user)
    else:
        return None


def login_forbidden(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_anonymous:
            return redirect(url_for('index.index_pages', path=''))
        return f(*args, **kwargs)

    return decorated


def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            raise APIUnauthorized("You must be logged in to access this endpoint")
        return f(*args, **kwargs)

    return decorated
