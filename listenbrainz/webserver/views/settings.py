import json
from datetime import datetime
from typing import Any

from flask import Blueprint, render_template, request, url_for, \
    redirect, current_app, jsonify, session
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest
import requests
from requests.adapters import HTTPAdapter, Retry

import listenbrainz.db.user as db_user
import listenbrainz.db.user_setting as db_usersetting
from data.model.external_service import ExternalServiceType
from listenbrainz.background.background_tasks import add_task
from listenbrainz.db import listens_importer
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.db.missing_musicbrainz_data import get_user_missing_musicbrainz_data
from listenbrainz.domain.apple import AppleService
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService, CRITIQUEBRAINZ_SCOPES
from listenbrainz.domain.external_service import ExternalService, ExternalServiceInvalidGrantError
from listenbrainz.domain.lastfm import LastfmService
from listenbrainz.domain.librefm import LibrefmService
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService
from listenbrainz.domain.spotify import SpotifyService, SPOTIFY_LISTEN_PERMISSIONS, SPOTIFY_IMPORT_PERMISSIONS
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.errors import APIServiceUnavailable, APINotFound, APIForbidden, APIInternalServerError, \
    APIBadRequest
from listenbrainz.webserver.login import api_login_required
from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.db import funkwhale as db_funkwhale


settings_bp = Blueprint("settings", __name__)


@settings_bp.post("/resettoken/")
@api_login_required
def reset_token():
    try:
        db_user.update_token(db_conn, current_user.id)
        return jsonify({"success": True})
    except DatabaseException:
        raise APIInternalServerError("Something went wrong! Unable to reset token right now.")


@settings_bp.post("/select_timezone/")
@api_login_required
def select_timezone():
    pg_timezones = db_usersetting.get_pg_timezone(db_conn)
    user_settings = db_usersetting.get(db_conn, current_user.id)
    user_timezone = user_settings['timezone_name']
    data = {
        "pg_timezones": pg_timezones,
        "user_timezone": user_timezone,
    }
    return jsonify(data)


@settings_bp.post("/troi/")
@login_required
def set_troi_prefs():
    current_troi_prefs = db_usersetting.get_troi_prefs(db_conn, current_user.id)
    data = {
        "troi_prefs": current_troi_prefs,
    }
    return jsonify(data)


@settings_bp.post("/import/")
@api_login_required
def import_data():
    """ Displays the import page to user, giving various options """
    user = db_user.get(db_conn, current_user.id, fetch_email=True)
    # if the flag is turned off (local development) then do not perform email check
    if current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"]:
        user_has_email = user["email"] is not None
    else:
        user_has_email = True

    data = {
        "user_has_email": user_has_email,
    }

    return jsonify(data)


@settings_bp.post('/delete/')
@api_login_required
@web_listenstore_needed
def delete():
    """ Delete currently logged-in user from ListenBrainz.

    If POST request, this view checks for the correct authorization token and
    deletes the user. If deletion is successful, redirects to home page, else
    flashes an error and redirects to user's info page.

    If GET request, this view renders a page asking the user to confirm
    that they wish to delete their ListenBrainz account.
    """
    try:
        add_task(current_user.id, "delete_user")
        return jsonify({"success": True})
    except Exception:
        current_app.logger.error('Error while deleting user: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f'Error while deleting user {current_user.musicbrainz_id}, please try again later.')


@settings_bp.post('/delete-listens/')
@api_login_required
@web_listenstore_needed
def delete_listens():
    """ Delete all the listens for the currently logged-in user from ListenBrainz.

    If POST request, this view checks for the correct authorization token and
    deletes the listens. If deletion is successful, redirects to user's profile page,
    else flashes an error and redirects to user's info page.

    If GET request, this view renders a page asking the user to confirm that they
    wish to delete their listens.
    """
    try:
        add_task(current_user.id, "delete_listens")
        return jsonify({"success": True})
    except Exception:
        current_app.logger.error('Error while deleting listens for user: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f"Error while deleting listens for user: {current_user.musicbrainz_id}")


def _get_service_or_raise_404(name: str, include_mb=False, exclude_apple=False) -> ExternalService:
    """Returns the music service for the given name and raise 404 if
    service is not found

    Args:
        name (str): Name of the service
    """
    try:
        service = ExternalServiceType[name.upper()]
        if service == ExternalServiceType.SPOTIFY:
            return SpotifyService()
        elif service == ExternalServiceType.CRITIQUEBRAINZ:
            return CritiqueBrainzService()
        elif service == ExternalServiceType.SOUNDCLOUD:
            return SoundCloudService()
        elif service == ExternalServiceType.LASTFM:
            return LastfmService()
        elif service == ExternalServiceType.LIBREFM:
            return LibrefmService()
        elif not exclude_apple and service == ExternalServiceType.APPLE:
            return AppleService()
        elif include_mb and service == ExternalServiceType.MUSICBRAINZ:
            return MusicBrainzService()
        elif service == ExternalServiceType.FUNKWHALE:
            return FunkwhaleService()
    except KeyError:
        raise NotFound("Service %s is invalid." % (name,))


@settings_bp.post('/music-services/details/')
@api_login_required
def music_services_details():
    spotify_service = SpotifyService()
    spotify_user = spotify_service.get_user(current_user.id)

    if spotify_user:
        permissions = set(spotify_user["scopes"])
        if permissions == SPOTIFY_IMPORT_PERMISSIONS:
            current_spotify_permissions = "import"
        elif permissions == SPOTIFY_LISTEN_PERMISSIONS:
            current_spotify_permissions = "listen"
        else:
            current_spotify_permissions = "both"
    else:
        current_spotify_permissions = "disable"

    critiquebrainz_service = CritiqueBrainzService()
    critiquebrainz_user = critiquebrainz_service.get_user(current_user.id)
    current_critiquebrainz_permissions = "review" if critiquebrainz_user else "disable"

    soundcloud_service = SoundCloudService()
    soundcloud_user = soundcloud_service.get_user(current_user.id)
    current_soundcloud_permissions = "listen" if soundcloud_user else "disable"

    apple_service = AppleService()
    apple_user = apple_service.get_user(current_user.id)
    current_apple_permissions = "listen" if apple_user and apple_user["refresh_token"] else "disable"

    lastfm_service = LastfmService()
    lastfm_user = lastfm_service.get_user(current_user.id)
    current_lastfm_permissions = "import" if lastfm_user else "disable"

    # For Funkwhale, check if user has any tokens (regardless of expiry)
    # This ensures we don't auto-disable when tokens are expired - let frontend handle reconnection
    funkwhale_servers = get_funkwhale_connections(current_user.id)
    funkwhale_host_urls = [server['host_url'] for server in funkwhale_servers] if funkwhale_servers else []
    
    # Check if user has any Funkwhale tokens (like other services do)
    funkwhale_tokens = db_funkwhale.get_all_user_tokens(current_user.id)
    current_funkwhale_permission = "listen" if funkwhale_tokens else "disable"

    librefm_service = LibrefmService()
    librefm_user = librefm_service.get_user(current_user.id)
    current_librefm_permissions = "import" if librefm_user else "disable"

    data: dict[str, Any] = {
        "current_spotify_permissions": current_spotify_permissions,
        "current_critiquebrainz_permissions": current_critiquebrainz_permissions,
        "current_soundcloud_permissions": current_soundcloud_permissions,
        "current_apple_permissions": current_apple_permissions,
        "current_lastfm_permissions": current_lastfm_permissions,
        "current_funkwhale_permission": current_funkwhale_permission,
        "funkwhale_host_urls": funkwhale_host_urls,
        "current_librefm_permissions": current_librefm_permissions,
    }
    if lastfm_user:
        data["current_lastfm_settings"] = {
            "external_user_id": lastfm_user["external_user_id"],
            "latest_listened_at": lastfm_user["latest_listened_at"],
        }
    if librefm_user:
        data["current_librefm_settings"] = {
            "external_user_id": librefm_user["external_user_id"],
            "latest_listened_at": librefm_user["latest_listened_at"],
        }

    return jsonify(data)


@settings_bp.get('/music-services/<service_name>/callback/')
@login_required
def music_services_callback(service_name: str):
    service = _get_service_or_raise_404(service_name, exclude_apple=True)

    # Check for error parameter first
    error = request.args.get('error')
    if error:
        return redirect(url_for('settings.index', path='music-services/details'))

    code = request.args.get('code')
    if not code:
        raise BadRequest('missing code')
    token = service.fetch_access_token(code)

    service.add_new_user(current_user.id, token)
    return redirect(url_for('settings.index', path='music-services/details'))


@settings_bp.post('/music-services/<service_name>/refresh/')
@api_login_required
def refresh_service_token(service_name: str):
    service = _get_service_or_raise_404(service_name, include_mb=True, exclude_apple=True)
    
    # Handle Funkwhale specially as it requires host_url parameter
    if service_name.lower() == 'funkwhale':
        data = request.get_json() or {}
        host_url = data.get('host_url')
        if not host_url:
            raise APIBadRequest("host_url is required for Funkwhale token refresh")
        
        try:
            user = service.get_user(current_user.id, host_url, refresh=True)
            if not user:
                raise APINotFound("User has not authenticated to Funkwhale at %s" % host_url)
        except ExternalServiceInvalidGrantError:
            raise APIForbidden("User has revoked authorization to Funkwhale")
        except Exception:
            current_app.logger.error("Unable to refresh Funkwhale token:", exc_info=True)
            raise APIServiceUnavailable("Cannot refresh Funkwhale token right now")
    else:
        user = service.get_user(current_user.id)
        if not user:
            raise APINotFound("User has not authenticated to %s" % service_name.capitalize())

        if service.user_oauth_token_has_expired(user):
            try:
                user = service.refresh_access_token(current_user.id, user["refresh_token"])
            except ExternalServiceInvalidGrantError:
                raise APIForbidden("User has revoked authorization to %s" % service_name.capitalize())
            except Exception:
                current_app.logger.error("Unable to refresh %s token:", exc_info=True)
                raise APIServiceUnavailable("Cannot refresh %s token right now" % service_name.capitalize())

    return jsonify({"access_token": user["access_token"]})


@settings_bp.post('/music-services/<service_name>/connect/')
@api_login_required
def music_services_connect(service_name: str):
    """ Connect last.fm/libre.fm account to ListenBrainz user. """
    if service_name.lower() not in {"lastfm", "librefm"}:
        raise APINotFound("Service %s is invalid." % (service_name,))

    data = request.json

    if "external_user_id" not in data:
        raise APIBadRequest("Missing 'external_user_id' in request.")

    latest_listened_at = None
    if data.get("latest_listened_at") is not None:
        try:
            latest_listened_at = datetime.fromisoformat(data["latest_listened_at"])
        except (ValueError, TypeError):
            raise APIBadRequest(f"Value of latest_listened_at '{data['latest_listened_at']} is invalid.")

    service = _get_service_or_raise_404(service_name)
    if service_name.lower() == "lastfm":
        api_key = current_app.config["LASTFM_API_KEY"]
        api_base_url = current_app.config["LASTFM_API_URL"]
    else:
        api_key = current_app.config["LIBREFM_API_KEY"]
        api_base_url = current_app.config["LIBREFM_API_URL"]

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=1, allowed_methods=["GET"])))

    params = {
        "method": "user.getrecenttracks",
        "user": data['external_user_id'],
        "format": "json",
        "api_key": api_key,
        "limit": 1,
    }
    if latest_listened_at:
        params["from"] = int(latest_listened_at.timestamp())
    response = session.get(api_base_url, params=params)
    if response.status_code == 404:
        raise APINotFound(f"User with username '{data['external_user_id']}' not found for service {service_name.capitalize()}.")

    service.add_new_user(current_user.id, {
        "external_user_id": data["external_user_id"],
        "latest_listened_at": latest_listened_at,
    })

    total_listens = 0
    try:
        lfm_data = response.json()
        total_listens = int(lfm_data["recenttracks"]["@attr"]["total"])
    except Exception:
        current_app.logger.error(f"Unable to fetch {service_name} user data:", exc_info=True)

    return jsonify({"success": True, "totalLfmListens": total_listens})


@settings_bp.post('/music-services/<service_name>/disconnect/')
@api_login_required
def music_services_disconnect(service_name: str):
    service = _get_service_or_raise_404(service_name)
    user = service.get_user(current_user.id)
    # this is to support the workflow of changing permissions in a single step
    # we delete the current permissions and then try to authenticate with new ones
    # we should try to delete the current permissions only if the user has connected previously
    if user:
        service.remove_user(current_user.id)

    try:
        action = json.loads(request.data).get('action', None)
    except json.JSONDecodeError:
        raise BadRequest('Invalid JSON')

    if not action or action == 'disable':
        return jsonify({"success": True})
    else:
        if service_name == 'spotify':
            permissions = None
            if action == 'both':
                permissions = SPOTIFY_LISTEN_PERMISSIONS | SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'import':
                permissions = SPOTIFY_IMPORT_PERMISSIONS
            elif action == 'listen':
                permissions = SPOTIFY_LISTEN_PERMISSIONS
            if permissions:
                return jsonify({"url": service.get_authorize_url(permissions)})
        elif service_name == 'soundcloud':
            return jsonify({"url": service.get_authorize_url([])})
        elif service_name == 'critiquebrainz':
            if action:
                return jsonify({"url": service.get_authorize_url(CRITIQUEBRAINZ_SCOPES)})
        elif service_name == 'apple':
            service.add_new_user(user_id=current_user.id)
            return jsonify({"success": True})
        elif service_name == 'funkwhale':
            if action:
                # For Funkwhale, we need to get the host URL from the request
                data = json.loads(request.data)
                host_url = data.get('host_url')
                if not host_url:
                    raise BadRequest('Missing host_url for Funkwhale')
                # Store host URL in session for callback
                session['funkwhale_host_url'] = host_url
                return jsonify({"url": service.get_authorize_url(host_url, [
                    'read:profile',
                    'read:libraries',
                    'read:favorites',
                    'read:listenings',
                    'read:follows',
                    'read:playlists',
                    'read:radios'
                ])})

    raise BadRequest('Invalid action')


@settings_bp.post('/music-services/<service_name>/set-token/')
@api_login_required
def music_services_set_token(service_name: str):
    if service_name != 'apple':
        raise APIInternalServerError("The set-token method not implemented for this service")

    music_user_token = request.data.decode('UTF-8')

    if not music_user_token:
        raise BadRequest('Missing user token in request body')

    apple_service = AppleService()
    apple_service.set_token(user_id=current_user.id, music_user_token=music_user_token)

    return jsonify({"success": True})


@settings_bp.post('/link-listens/')
@api_login_required
def link_listens():
    """ Returns a list of unlinked listens for the user """
    unlinked_listens, created = get_user_missing_musicbrainz_data(db_conn, ts_conn, current_user.id, "cf")
    data = {
        "unlinked_listens": unlinked_listens or [],
        "last_updated": created,
    }
    return jsonify(data)


@settings_bp.get('/', defaults={'path': ''})
@settings_bp.get('/<path:path>/')
@login_required
def index(path):
    return render_template("index.html")


def get_funkwhale_connections(user_id):
    # Returns a list of dicts for all Funkwhale connections for a user
    from sqlalchemy import text
    from listenbrainz.webserver import db_conn
    result = db_conn.execute(text('''
        SELECT s.* FROM funkwhale_tokens t
        JOIN funkwhale_servers s ON t.funkwhale_server_id = s.id
        WHERE t.user_id = :user_id
    '''), {'user_id': user_id})
    return [dict(row) for row in result.mappings().all()]
