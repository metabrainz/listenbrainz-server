import logging
from datetime import timezone

from data.model.external_service import ExternalService
from listenbrainz.db import external_service as db_service

from flask import current_app
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


youtube_scopes = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_authorize_url():
    flow = Flow.from_client_config(current_app.config["YOUTUBE_CONFIG"],
                                   scopes=youtube_scopes,
                                   redirect_uri="http://localhost/profile/connect-youtube/callback/")

    # TODO: look into state
    authorization_url, _ = flow.authorization_url(access_type="offline",
                                                  include_granted_scopes="true")
    return authorization_url


def fetch_access_token(code):
    flow = Flow.from_client_config(current_app.config["YOUTUBE_CONFIG"],
                                   scopes=youtube_scopes,
                                   redirect_uri="http://localhost/profile/connect-youtube/callback/")
    token = flow.fetch_token(code=code)
    logging.error(token)
    return token


def refresh_token(user_id):
    client = current_app.config["YOUTUBE_CONFIG"]["web"]
    user = get_user(user_id)
    credentials = Credentials(token=user["access_token"], refresh_token=user["refresh_token"],
                              client_id=client["client_id"], client_secret=client["client_secret"],
                              token_uri=client["token_uri"], scopes=youtube_scopes,
                              expiry=user["token_expires"])
    logging.error(credentials)

    credentials.refresh(Request())
    db_service.update_token(user_id=user_id, service=ExternalService.YOUTUBE, access_token=credentials.token,
                            refresh_token=credentials.refresh_token,
                            expires_at=int(credentials.expiry.replace(tzinfo=timezone.utc).timestamp()))

    logging.error(credentials)
    return get_user(user_id)


def add_new_user(user_id, token):
    db_service.save_token(user_id=user_id, service=ExternalService.YOUTUBE, access_token=token["access_token"],
                          refresh_token=token["refresh_token"], token_expires_ts=int(token["expires_at"]),
                          record_listens=False, service_details={"scopes": token["scope"]})


def remove_user(user_id):
    db_service.delete_token(user_id=user_id, service=ExternalService.YOUTUBE)


def get_user(user_id):
    return db_service.get_token(user_id=user_id, service=ExternalService.YOUTUBE)

