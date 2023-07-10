from datetime import datetime, timedelta

import jwt
from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth
from listenbrainz.domain.external_service import ExternalService

DEVELOPER_TOKEN_VALIDITY = timedelta(days=180)


class AppleService(ExternalService):

    def __init__(self):
        super(AppleService, self).__init__(ExternalServiceType.APPLE)
        self.apple_music_key = current_app.config["APPLE_MUSIC_KEY"]
        self.apple_music_kid = current_app.config["APPLE_MUSIC_KID"]
        self.apple_music_team_id = current_app.config["APPLE_MUSIC_TEAM_ID"]

    def generate_developer_token(self):
        """ Generate an Apple Music JWT token for use with Apple Music API """
        iat = datetime.now()
        exp = iat + DEVELOPER_TOKEN_VALIDITY

        iat = int(iat.timestamp())
        exp = int(exp.timestamp())

        token = jwt.encode(
            {"iss": self.apple_music_team_id, "iat": iat, "exp": exp},
            self.apple_music_key,
            "ES256",
            headers={"kid": self.apple_music_kid}
        )
        return {"access_token": token, "expires_at": exp}

    def add_new_user(self, user_id: int, token: dict) -> bool:
        """ Create a new apple music row to store a user specific developer token

        Args:
            user_id: A flask auth `current_user.id`
            token: A dict containing jwt encoded token and its expiry time
        """
        access_token = token["access_token"]
        expires_at = token["expires_at"]
        external_service_oauth.save_token(
            user_id=user_id, service=self.service, access_token=access_token,
            refresh_token=None, token_expires_ts=expires_at, record_listens=False,
            scopes=[], external_user_id=None
        )
        return True

    def revoke_user(self, user_id: int):
        """ Delete the user's connection to external service but retain
        the last import error message.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        external_service_oauth.delete_token(user_id, self.service, remove_import_log=False)

    def update_music_user_token(self, user_id: int, music_user_token: str):
        """ Update the music user token for the given user. """
        token = self.get_user(user_id)
        external_service_oauth.update_token(
            user_id=user_id,
            service=ExternalServiceType.APPLE,
            access_token=token["access_token"],
            refresh_token=music_user_token,
            expires_at=int(token["token_expires"].timestamp())
        )
