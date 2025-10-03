import hashlib
import json
import time
from typing import Optional
from cryptography.fernet import Fernet

import requests
from flask import current_app

from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.webserver import db_conn
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError

NAVIDROME_API_RETRIES = 3


class NavidromeService:

    def __init__(self):
        _encryption_key = current_app.config.get("NAVIDROME_ENCRYPTION_KEY")
        self.encryption_key = _encryption_key.encode("utf-8") if _encryption_key else None

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for storage"""
        f = Fernet(self.encryption_key)
        return f.encrypt(password.encode("utf-8")).decode("utf-8")

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password for API requests"""
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_password.encode("utf-8")).decode("utf-8")

    @staticmethod
    def generate_token(password: str) -> tuple[str, str]:
        """Generate fresh token for API requests

            Args:
                password: plaintext password

            Returns: tuple of token and salt
        """
        salt = str(int(time.time() * 1000))
        raw_token = password + salt
        token = hashlib.md5(raw_token.encode("utf-8")).hexdigest()
        return token, salt

    def authenticate(self, host_url: str, username: str, password: str) -> str:
        """Test provided credentials with Navidrome using Subsonic API and return
           the encrypted password if valid."""
        try:
            token, salt = self.generate_token(password)

            # Test authentication with a ping request
            base_url = host_url.rstrip('/')
            ping_url = f"{base_url}/rest/ping"
            params = {
                "u": username,
                "t": token,
                "s": salt,
                "v": "1.16.0",
                "c": "ListenBrainz",
                "f": "json"
            }

            response = requests.get(ping_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "subsonic-response" not in data:
                raise ExternalServiceError("Invalid response from Navidrome server: %s", json.dumps(data))

            subsonic_response = data["subsonic-response"]
            if subsonic_response.get("status") != "ok":
                error = subsonic_response.get("error", {})
                error_message = error.get("message", "Authentication failed")
                raise ExternalServiceError(error_message)

            return self._encrypt_password(password)
        except requests.exceptions.RequestException as e:
            raise ExternalServiceAPIError(f"Unable to connect to server: {str(e)}")
        except ExternalServiceError:
            raise
        except Exception as e:
            raise ExternalServiceError(f"Authentication error: {str(e)}")

    def connect_user(self, user_id: int, host_url: str, username: str, password: str) -> int:
        """Connect a user to Navidrome (one connection per user)"""
        try:
            normalized_host_url = host_url.rstrip('/')
            encrypted_password = self.authenticate(normalized_host_url, username, password)
            token_id = db_navidrome.save_user_token(
                db_conn,
                user_id=user_id,
                host_url=normalized_host_url,
                username=username,
                encrypted_password=encrypted_password
            )
            return token_id
        except (ExternalServiceError, ExternalServiceAPIError):
            raise
        except Exception as e:
            raise ExternalServiceError(f"Connection failed: {str(e)}")

    def get_user(self, user_id: int, include_token: bool = True) -> Optional[dict[str, str]]:
        """Retrieve navidrome connection details and generate fresh authentication parameters,
           if include_token is True, to make API requests.
        """
        try:
            connection = db_navidrome.get_user_token(db_conn, user_id)
            if not connection:
                return None

            if include_token:
                encrypted_password = connection["encrypted_password"]
                password = self._decrypt_password(encrypted_password)
                token, salt = self.generate_token(password)
            else:
                token, salt = None, None

            instance_url = connection["host_url"].rstrip('/')

            return {
                "md5_auth_token": token,
                "salt": salt,
                "instance_url": instance_url,
                "username": connection["username"],
            }
        except Exception as e:
            current_app.logger.error(f"Failed to generate auth params for user {user_id}: {str(e)}")
            return None

    def remove_user(self, user_id: int):
        """Remove user's Navidrome connection (same as Funkwhale)"""
        try:
            db_navidrome.delete_user_token(db_conn, user_id)
        except Exception as e:
            current_app.logger.error(f"Failed to remove Navidrome token for user {user_id}: {str(e)}")
            raise