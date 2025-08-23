import hashlib
import time
import base64
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from cryptography.fernet import Fernet

import requests
from flask import current_app

from listenbrainz.db import navidrome as db_navidrome
from listenbrainz.webserver import db_conn
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError

NAVIDROME_API_RETRIES = 3


class NavidromeService:
    def __init__(self):
        # Get encryption key for password storage
        self.encryption_key = self._get_encryption_key()

    def _get_encryption_key(self):
        """Get encryption key from config"""
        key = current_app.config.get('NAVIDROME_ENCRYPTION_KEY')
        
        # Ensure key is properly encoded for Fernet
        if isinstance(key, str):
            key = key.encode('utf-8')
        return key

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for storage"""
        f = Fernet(self.encryption_key)
        return f.encrypt(password.encode('utf-8')).decode('utf-8')

    def _decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password for API requests"""
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')

    def _generate_auth_params(self, username: str, password: str) -> Dict[str, str]:
        """Generate fresh authentication parameters for each request"""
        # Generate random salt (timestamp-based)
        salt = str(int(time.time() * 1000))
        
        # Create MD5 hash of password + salt
        token = hashlib.md5((password + salt).encode('utf-8')).hexdigest()
        
        return {
            'username': username,
            'token': token,
            'salt': salt
        }

    def authenticate(self, host_url: str, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with Navidrome using Subsonic API and basic auth"""
        try:
            # Ensure host_url has proper format
            if not host_url.startswith(('http://', 'https://')):
                # For localhost and local IPs, use http; for domains, use https
                if host_url.startswith(('localhost', '127.0.0.1', '192.168.', '10.', '172.')):
                    host_url = 'http://' + host_url
                else:
                    host_url = 'https://' + host_url
            
            # Clean up trailing slash
            host_url = host_url.rstrip('/')
            
            # Generate auth parameters with random salt
            auth_params = self._generate_auth_params(username, password)
            
            # Test authentication with ping request
            ping_url = urljoin(host_url, '/rest/ping')
            params = {
                'u': auth_params['username'],
                't': auth_params['token'],
                's': auth_params['salt'],
                'v': '1.16.0',  # Subsonic API version
                'c': 'ListenBrainz',  # Client
                'f': 'json'
            }
            
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
                
                raise ExternalServiceError(error_message)
            
            # Return authentication data with encrypted password
            return {
                'host_url': host_url,
                'username': username,
                'encrypted_password': self._encrypt_password(password),
                'server_version': subsonic_response.get('version', 'unknown')
            }
            
        except requests.exceptions.RequestException as e:
            raise ExternalServiceAPIError(f"Unable to connect to server: {str(e)}")
        except ExternalServiceError:
            raise
        except Exception as e:
            raise ExternalServiceError(f"Authentication error: {str(e)}")

    def connect_user(self, user_id: int, host_url: str, username: str, password: str) -> Dict[str, Any]:
        """Connect a user to Navidrome (one connection per user)"""
        try:
            # Authenticate with Navidrome
            auth_data = self.authenticate(host_url, username, password)
            
            # Save encrypted password (not token)
            token_id = db_navidrome.save_user_token(
                db_conn,
                user_id=user_id,
                host_url=auth_data['host_url'],
                username=username,
                encrypted_password=auth_data['encrypted_password']
            )
            
            return {
                'success': True,
                'host_url': auth_data['host_url'],
                'username': username,
                'server_version': auth_data.get('server_version'),
                'token_id': token_id
            }
            
        except (ExternalServiceError, ExternalServiceAPIError):
            raise
        except Exception as e:
            raise ExternalServiceError(f"Connection failed: {str(e)}")

    def get_user_connection(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's Navidrome connection (only one per user)"""
        try:
            token_data = db_navidrome.get_user_token(db_conn, user_id)
            if not token_data:
                return None
            
            return {
                'host_url': token_data['host_url'],
                'username': token_data['username'],
                'encrypted_password': token_data['encrypted_password'],
                'connected': True,
                'permissions': ['listen']
            }
            
        except Exception as e:
            current_app.logger.error(f"Failed to get Navidrome connection for user {user_id}: {str(e)}")
            return None

    def get_auth_params_for_user(self, user_id: int) -> Optional[Dict[str, str]]:
        """Generate fresh authentication parameters for a user's API requests"""
        try:
            token_data = db_navidrome.get_user_token(db_conn, user_id)
            if not token_data:
                return None
            
            # Decrypt stored password
            encrypted_password = token_data['encrypted_password']
            password = self._decrypt_password(encrypted_password)
            username = token_data['username']
            
            # Generate fresh auth params with new salt
            return self._generate_auth_params(username, password)
            
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
