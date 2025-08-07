import hashlib
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
from flask import current_app

from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.webserver import db_conn
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError

NAVIDROME_API_RETRIES = 3


class NavidromeService:
    def __init__(self):
        pass

    def authenticate(self, host_url: str, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with Navidrome using Subsonic API and basic auth"""
        try:
            current_app.logger.info(f"Navidrome auth attempt - Original host_url: '{host_url}'")
            
            # Ensure host_url has proper format
            if not host_url.startswith(('http://', 'https://')):
                # For localhost and local IPs, use http; for domains, use https
                if host_url.startswith(('localhost', '127.0.0.1', '192.168.', '10.', '172.')):
                    host_url = 'http://' + host_url
                else:
                    host_url = 'https://' + host_url
            
            # Clean up trailing slash
            host_url = host_url.rstrip('/')
            
            current_app.logger.info(f"Navidrome auth attempt - Processed host_url: '{host_url}'")
            
            # Create MD5 hash token (salt + password)
            salt = str(int(time.time() * 1000))  # Use timestamp as salt
            token = hashlib.md5((password + salt).encode('utf-8')).hexdigest()
            
            # Test authentication with ping request
            ping_url = urljoin(host_url, '/rest/ping')
            current_app.logger.info(f"Navidrome auth attempt - Final ping_url: '{ping_url}'")
            params = {
                'u': username,
                't': token,
                's': salt,
                'v': '1.16.0',  # Subsonic API version
                'c': 'ListenBrainz',  # Client
                'f': 'json'
            }
            
            current_app.logger.info(f"Attempting to connect to Navidrome at: {ping_url}")
            response = requests.get(ping_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if response contains error
            if 'subsonic-response' not in data:
                raise ExternalServiceError("Invalid response from Navidrome server")
            
            subsonic_response = data['subsonic-response']
            if subsonic_response.get('status') != 'ok':
                error = subsonic_response.get('error', {})
                error_message = error.get('message', 'Authentication failed')
                raise ExternalServiceError(f"Navidrome authentication failed: {error_message}")
            
            # Return authentication data
            return {
                'host_url': host_url,
                'username': username,
                'token': token,
                'salt': salt,
                'server_version': subsonic_response.get('version', 'unknown')
            }
            
        except requests.exceptions.RequestException as e:
            raise ExternalServiceAPIError(f"Failed to connect to Navidrome server: {str(e)}")
        except Exception as e:
            raise ExternalServiceError(f"Navidrome authentication error: {str(e)}")

    def connect_user(self, user_id: int, host_url: str, username: str, password: str) -> Dict[str, Any]:
        """Connect a user to Navidrome (one connection per user)"""
        try:
            # Authenticate with Navidrome
            auth_data = self.authenticate(host_url, username, password)
            
            # Save user token (replaces any existing connection)
            token_id = db_navidrome.save_user_token(
                user_id=user_id,
                host_url=auth_data['host_url'],
                username=username,
                access_token=auth_data['token']
            )
            
            return {
                'success': True,
                'host_url': auth_data['host_url'],
                'username': username,
                'server_version': auth_data.get('server_version'),
                'token_id': token_id
            }
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to connect to Navidrome: {str(e)}")

    def get_user_connection(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's Navidrome connection (only one per user)"""
        try:
            token_data = db_navidrome.get_user_token(user_id)
            if not token_data:
                return None
            
            return {
                'host_url': token_data['host_url'],
                'username': token_data['username'],
                'connected': True,
                'permissions': ['listen']
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get Navidrome connection for user {user_id}: {str(e)}")
            return None

    def remove_user(self, user_id: int):
        """Remove user's Navidrome connection (same as Funkwhale)"""
        try:
            db_navidrome.delete_user_token(user_id)
        except Exception as e:
            current_app.logger.error(f"Failed to remove Navidrome token for user {user_id}: {str(e)}")
            raise
