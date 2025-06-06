from flask import Blueprint, jsonify, request, current_app
from brainzutils.ratelimit import ratelimit

from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import validate_auth_header
from listenbrainz.webserver.errors import APIBadRequest, APINotFound

funkwhale_api_bp = Blueprint('funkwhale_api_v1', __name__)

@funkwhale_api_bp.route('/connect', methods=['POST'])
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
        
        host_url = data['host_url']
        service = FunkwhaleService()
        auth_url = service.get_authorize_url(host_url, ['read:listens'])
        
        return jsonify({
            'status': 'ok',
            'auth_url': auth_url
        })
    except Exception as e:
        raise APIBadRequest(str(e))

@funkwhale_api_bp.route('/callback', methods=['GET'])
@crossdomain
@ratelimit()
def funkwhale_callback():
    """Handle the OAuth callback from Funkwhale.
    
    This endpoint is called by Funkwhale after the user authorizes the application.
    The request should contain the following query parameters:
    - code: The authorization code from Funkwhale
    - host_url: The Funkwhale server URL
    
    Returns:
        A JSON response indicating success or failure.
    """
    user = validate_auth_header()
    
    try:
        code = request.args.get('code')
        host_url = request.args.get('host_url')
        if not code:
            raise APIBadRequest("Missing authorization code")
        if not host_url:
            raise APIBadRequest("Missing host_url")
        
        service = FunkwhaleService()
        token = service.fetch_access_token(host_url, code)
        service.add_new_user(user['id'], host_url, token)
        
        return jsonify({
            'status': 'ok',
            'message': 'Successfully connected to Funkwhale'
        })
    except Exception as e:
        raise APIBadRequest(str(e))

@funkwhale_api_bp.route('/disconnect', methods=['POST'])
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
        
        host_url = data['host_url']
        service = FunkwhaleService()
        service.revoke_user(user['id'], host_url)
        
        return jsonify({
            'status': 'ok',
            'message': 'Successfully disconnected from Funkwhale'
        })
    except Exception as e:
        raise APIBadRequest(str(e))

@funkwhale_api_bp.route('/status', methods=['GET'])
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
    except Exception as e:
        raise APIBadRequest(str(e)) 