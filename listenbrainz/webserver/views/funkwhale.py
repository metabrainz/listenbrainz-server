from flask import Blueprint, jsonify, request, current_app, redirect, url_for, session
from brainzutils.ratelimit import ratelimit
import logging
import base64
import os

from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import validate_auth_header
from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APIInternalServerError
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, ExternalServiceInvalidGrantError

funkwhale_api_bp = Blueprint('funkwhale_api_v1', __name__)

@funkwhale_api_bp.route('/connect/', methods=['POST'])
@crossdomain
@ratelimit()
def connect_funkwhale():
    """Connect a user's ListenBrainz account to Funkwhale.
    
    The request should contain the following JSON data:
    {
        "host_url": "https://funkwhale.example.com"
    }
    
    Returns:
        A JSON response with the authorization URL to redirect the user to.
    """
    user = validate_auth_header()
    
    try:
        data = request.get_json()
        if not data or 'host_url' not in data:
            raise APIBadRequest("Missing host_url in request")
        
        host_url = data['host_url'].rstrip('/')
        service = FunkwhaleService()
        
        # Generate a state parameter for security
        state = base64.b64encode(os.urandom(32)).decode('utf-8')
        session['funkwhale_state'] = state
        session['funkwhale_host_url'] = host_url
        
        # Get the authorization URL with state parameter and required scopes
        auth_url = service.get_authorize_url(
            host_url=host_url,
            scopes=['read:listens', 'read:profile'],  # Add required scopes
            state=state
        )
        
        return jsonify({
            'status': 'ok',
            'auth_url': auth_url
        })
    except APIBadRequest as e:
        raise e
    except Exception as e:
        current_app.logger.error("Error in connect_funkwhale: %s", str(e), exc_info=True)
        raise APIInternalServerError("An error occurred while connecting to Funkwhale")

@funkwhale_api_bp.route('/disable/', methods=['POST'])
@crossdomain
@ratelimit()
def disconnect_funkwhale():
    """Disconnect a user's ListenBrainz account from Funkwhale.
    
    The request should contain the following JSON data:
    {
        "host_url": "https://funkwhale.example.com"
    }
    """
    user = validate_auth_header()
    
    try:
        data = request.get_json()
        if not data or 'host_url' not in data:
            raise APIBadRequest("Missing host_url in request")
        
        host_url = data['host_url'].rstrip('/')
        service = FunkwhaleService()
        service.revoke_user(user['id'], host_url)
        
        return jsonify({
            'status': 'ok',
            'message': 'Successfully disconnected from Funkwhale'
        })
    except APIBadRequest as e:
        raise e
    except Exception as e:
        current_app.logger.error("Error in disconnect_funkwhale: %s", str(e), exc_info=True)
        raise APIInternalServerError("An error occurred while disconnecting from Funkwhale")

@funkwhale_api_bp.route('/status/', methods=['GET'])
@crossdomain
@ratelimit()
def get_funkwhale_status():
    """Get the status of a user's Funkwhale connection.
    
    The request should contain the following query parameters:
    - host_url: The Funkwhale server URL
    """
    user = validate_auth_header()
    
    try:
        host_url = request.args.get('host_url')
        if not host_url:
            raise APIBadRequest("Missing host_url")
        
        host_url = host_url.rstrip('/')
        service = FunkwhaleService()
        connection = service.get_user(user['id'], host_url)
        
        if not connection:
            raise APINotFound("No Funkwhale connection found")
        
        return jsonify({
            'status': 'ok',
            'connection': {
                'user_id': connection['user_id'],
                'host_url': connection['host_url'],
                'token_expiry': connection['token_expiry']
            }
        })
    except (APIBadRequest, APINotFound) as e:
        raise e
    except Exception as e:
        current_app.logger.error("Error in get_funkwhale_status: %s", str(e), exc_info=True)
        raise APIInternalServerError("An error occurred while getting Funkwhale status") 