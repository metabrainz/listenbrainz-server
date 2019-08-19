from rauth import OAuth2Service
from flask import request, session, url_for
from listenbrainz.webserver.login import User
from listenbrainz.webserver.utils import generate_string
import listenbrainz.db.user as db_user
import ujson

_musicbrainz = None
_session_key = None


def init(client_id, client_secret, session_key='musicbrainz'):
    global _musicbrainz, _session_key
    _musicbrainz = OAuth2Service(
        name='musicbrainz',
        base_url="https://musicbrainz.org/",
        authorize_url="https://musicbrainz.org/oauth2/authorize",
        access_token_url="https://musicbrainz.org/oauth2/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    _session_key = session_key


def get_user():
    """Function should fetch user data from database, or, if necessary, create it, and return it."""
    s = _musicbrainz.get_auth_session(data={
        'code': _fetch_data('code'),
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('login.musicbrainz_post', _external=True)
    }, decoder=lambda b: ujson.loads(b.decode("utf-8")))
    data = s.get('oauth2/userinfo').json()
    musicbrainz_id = data.get('sub')
    musicbrainz_row_id = data.get('metabrainz_user_id')
    user = db_user.get_or_create(musicbrainz_row_id, musicbrainz_id)
    if user:
        if not user['musicbrainz_row_id']:
            db_user.update_musicbrainz_row_id(musicbrainz_id, data['metabrainz_user_id'])

        # if the musicbrainz_id of the user from MusicBrainz is different, we need
        # to update it here too
        if user['musicbrainz_id'] != musicbrainz_id:
            db_user.update_musicbrainz_id(user['id'], musicbrainz_id)

        return User.from_dbrow(user)
    else:
        return None


def get_authentication_uri():
    """Prepare and return URL to authentication service login form."""
    csrf = generate_string(20)
    _persist_data(csrf=csrf)
    params = {
        'response_type': 'code',
        'redirect_uri': url_for('login.musicbrainz_post', _external=True),
        'scope': 'profile',
        'state': csrf,
    }
    return _musicbrainz.get_authorize_url(**params)


def validate_post_login():
    """Function validating parameters passed in uri query after redirection from login form.
    Should return True, if everything is ok, or False, if something went wrong.
    """
    if request.args.get('error'):
        return False
    if _fetch_data('csrf') != request.args.get('state'):
        return False
    code = request.args.get('code')
    if not code:
        return False
    _persist_data(code=code)
    return True


def _persist_data(**kwargs):
    """Save data in session."""
    if _session_key not in session:
        session[_session_key] = dict()
    session[_session_key].update(**kwargs)
    session.modified = True


def _fetch_data(key, default=None):
    """Fetch data from session."""
    if _session_key not in session:
        return None
    else:
        return session[_session_key].get(key, default)
