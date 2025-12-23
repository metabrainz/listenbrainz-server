import hashlib
import json
import time
from typing import Optional
import xml.etree.ElementTree as ET
from datetime import datetime
import requests

from cryptography.fernet import Fernet
from flask import current_app

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.navidrome as db_navidrome
from listenbrainz.webserver import db_conn
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper, MATCH_TYPE_MED_QUALITY, MATCH_TYPE_HIGH_QUALITY, MATCH_TYPE_EXACT_MATCH
from listenbrainz.domain.external_service import ExternalServiceError

class NavidromeService:
    def _get_cipher_suite(self):
        key = current_app.config["NAVIDROME_ENCRYPTION_KEY"]
        if not key:
            raise ExternalServiceError("Navidrome encryption key not configured")
        return Fernet(key)

    def get_user(self, user_id: int, include_token: bool = False) -> Optional[dict]:
        token = db_navidrome.get_user_token(db_conn, user_id)
        if not token:
            return None
        
        details = {
            "user_id": user_id,
            "host_url": token["host_url"],
            "instance_url": token["host_url"],
            "username": token["username"],
        }
        
        if include_token:
            details["encrypted_password"] = token["encrypted_password"]
            
        return details

    def connect_user(self, user_id: int, host_url: str, username: str, password: str):
        cipher_suite = self._get_cipher_suite()
        encrypted_password = cipher_suite.encrypt(password.encode()).decode()
        db_navidrome.save_user_token(db_conn, user_id, host_url, username, encrypted_password)

    def remove_user(self, user_id: int):
        db_navidrome.delete_user_token(db_conn, user_id)

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