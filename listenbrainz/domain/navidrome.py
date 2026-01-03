import hashlib
import json
import time
from typing import Optional
import xml.etree.ElementTree as ET
from datetime import datetime
from cryptography.fernet import Fernet

import requests
from flask import current_app

from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.webserver import db_conn
import listenbrainz.db.feedback as db_feedback
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper, MATCH_TYPE_MED_QUALITY, MATCH_TYPE_HIGH_QUALITY, MATCH_TYPE_EXACT_MATCH

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


def import_starred_tracks(user_id, navidrome_url, auth_token, salt, username):
    """
    Import starred songs from Navidrome.
    
    Args:
        user_id (int): The ListenBrainz user ID.
        navidrome_url (str): The Navidrome server URL.
        auth_token (str): The Subsonic auth token (md5(password + salt)).
        salt (str): The salt used for the auth token.
        username (str): The Navidrome username.
        
    Returns:
        dict: A dictionary containing 'total_found', 'total_mapped', and 'total_imported'.
    """
    mapper = MBIDMapper()
    
    # Subsonic API parameters
    params = {
        'u': username,
        't': auth_token,
        's': salt,
        'v': '1.16.1',
        'c': 'ListenBrainz',
        'f': 'xml'
    }
    
    api_url = f"{navidrome_url.rstrip('/')}/rest/getStarred"
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ExternalServiceError(f"Failed to fetch starred songs from Navidrome: {str(e)}")
        
    xml_content = response.content
    root = ET.fromstring(xml_content)
    
    # Handle namespace if present
    ns = {}
    if root.tag.startswith("{http://subsonic.org/restapi}"):
        ns = {'s': 'http://subsonic.org/restapi'}
        songs = root.findall(".//s:starred2/s:song", ns)
        if not songs:
            songs = root.findall(".//s:starred/s:song", ns)
    else:
        songs = root.findall(".//starred2/song")
        if not songs:
            songs = root.findall(".//starred/song")
        
    total_found = len(songs)
    total_mapped = 0
    total_imported = 0
    feedback_to_insert = []
    
    for song in songs:
        artist = song.get("artist")
        title = song.get("title")
        album = song.get("album")
        starred_date = song.get("starred")
        
        if not artist or not title:
            continue
            
        match = mapper.search(artist, title, album)
        
        if match and match['match_type'] in (MATCH_TYPE_MED_QUALITY, MATCH_TYPE_HIGH_QUALITY, MATCH_TYPE_EXACT_MATCH):
            recording_mbid = match['recording_mbid']
            total_mapped += 1
            
            try:
                if starred_date:
                    dt = datetime.fromisoformat(starred_date.replace("Z", "+00:00"))
                    timestamp = int(dt.timestamp())
                else:
                    timestamp = int(datetime.now().timestamp())
            except (ValueError, TypeError):
                timestamp = int(datetime.now().timestamp())
                
            feedback_to_insert.append((timestamp, recording_mbid))
            
    if feedback_to_insert:
        db_feedback.bulk_insert_loved_tracks(db_conn, user_id, feedback_to_insert)
        total_imported = len(feedback_to_insert)
        
    return {
        "total_found": total_found,
        "total_mapped": total_mapped,
        "total_imported": total_imported
    }