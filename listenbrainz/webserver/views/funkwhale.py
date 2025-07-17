from flask import Blueprint, jsonify, request, current_app, redirect, url_for, session
from brainzutils.ratelimit import ratelimit
import logging
import base64
import os
from urllib.parse import urlparse

from listenbrainz.domain.funkwhale import FunkwhaleService
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import validate_auth_header
from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APIInternalServerError, APIUnauthorized, APIForbidden, APIServiceUnavailable
from listenbrainz.domain.external_service import ExternalServiceError, ExternalServiceAPIError, ExternalServiceInvalidGrantError
from listenbrainz.db import funkwhale as db_funkwhale

funkwhale_api_bp = Blueprint('funkwhale_api_v1', __name__)

def validate_funkwhale_url(url: str) -> str:
    """Validate of Funkwhale server URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        The normalized URL
        
    Raises:
        APIBadRequest: If the URL is invalid
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise APIBadRequest("Invalid Funkwhale server URL. Must include scheme (http:// or https://) and hostname.")
        
        # Allow HTTP for localhost and development environments
        if parsed.scheme != 'https' and not (parsed.netloc.startswith('localhost') or parsed.netloc.startswith('127.0.0.1')):
            raise APIBadRequest("Funkwhale server URL must use HTTPS unless it's localhost")
            
        # Normalize the URL
        normalized = f"{parsed.scheme}://{parsed.netloc}"
        return normalized.rstrip('/')
    except Exception as e:
        raise APIBadRequest(f"Invalid Funkwhale server URL: {str(e)}")

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
    try:
        # Validate auth token
        user = validate_auth_header()
        if not user:
            current_app.logger.error("No valid auth token provided")
            return jsonify({
                'status': 'error',
                'error': 'You must be logged in to connect to Funkwhale'
            }), 401

        # Parse and validate request data
        try:
            data = request.get_json()
            current_app.logger.info("Received connect request with data: %s", data)
        except Exception as e:
            current_app.logger.error("Error parsing JSON in connect_funkwhale: %s", str(e))
            return jsonify({
                'status': 'error',
                'error': 'Invalid JSON in request'
            }), 400

        if not data or 'host_url' not in data:
            current_app.logger.error("Missing host_url in request data")
            return jsonify({
                'status': 'error',
                'error': 'Missing host_url in request'
            }), 400
        
        # Validate host URL
        try:
            host_url = validate_funkwhale_url(data['host_url'])
        except APIBadRequest as e:
            current_app.logger.error("Invalid host URL: %s", str(e))
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 400

        # Check if Funkwhale configuration is set up
        if not current_app.config.get('FUNKWHALE_CALLBACK_URL'):
            current_app.logger.error("FUNKWHALE_CALLBACK_URL not configured")
            return jsonify({
                'status': 'error',
                'error': 'Funkwhale integration is not properly configured'
            }), 500

        # Initialize service and generate state
        try:
            service = FunkwhaleService()
            state = base64.b64encode(os.urandom(32)).decode('utf-8')
            current_app.logger.info("Generated state for Funkwhale connection: %s", state)
        
            # Store only serializable data in session
            session['funkwhale_state'] = state
            session['funkwhale_host_url'] = host_url
            session['funkwhale_user_id'] = user['id']  # Store only the user ID
            current_app.logger.info("Stored session data for user %s", user['id'])
        
            # Get authorization URL with parent scope
            try:
                auth_url = service.get_authorize_url(
                    host_url=host_url,
                    scopes=[
                        'read:profile',
                        'read:libraries',
                        'read:favorites',
                        'read:listenings',
                        'read:follows',
                        'read:playlists',
                        'read:radios'
                    ],
                    state=state
                )
                current_app.logger.info("Generated authorization URL: %s", auth_url)
            except Exception as e:
                current_app.logger.error("Error generating authorization URL: %s", str(e), exc_info=True)
                return jsonify({
                    'status': 'error',
                    'error': f'Failed to generate authorization URL: {str(e)}'
                }), 500
        
            return jsonify({
                'status': 'ok',
                'url': auth_url  
            }), 200
        except Exception as e:
            current_app.logger.error("Error in FunkwhaleService: %s", str(e), exc_info=True)
            return jsonify({
                'status': 'error',
                'error': f'An error occurred while connecting to Funkwhale: {str(e)}'
            }), 500

    except Exception as e:
        current_app.logger.error("Unexpected error in connect_funkwhale: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500

@funkwhale_api_bp.route('/disconnect/', methods=['POST'])
@crossdomain
@ratelimit()
def disconnect_funkwhale():
    """Disconnect a user's ListenBrainz account from all Funkwhale servers.
    This will delete all Funkwhale tokens and server associations for the user.
    """
    user = validate_auth_header()
    try:
        service = FunkwhaleService()
        service.remove_user(user['id'])
        return jsonify({
            'status': 'ok',
            'message': 'Successfully disconnected from Funkwhale'
        })
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
        
        # Validate and normalize the host URL
        host_url = validate_funkwhale_url(host_url)
        
        service = FunkwhaleService()
        connection = service.get_user(user['id'], host_url, refresh=True)  # Auto-refresh if expired
        
        if not connection:
            raise APINotFound("No Funkwhale connection found")
        
        return jsonify({
            'status': 'ok',
            'connection': {
                'user_id': connection['user_id'],
                'host_url': connection['host_url'],
                'access_token': connection['access_token'],
                'token_expiry': connection['token_expiry']
            }
        })
    except (APIBadRequest, APINotFound) as e:
        raise e
    except Exception as e:
        current_app.logger.error("Error in get_funkwhale_status: %s", str(e), exc_info=True)
        raise APIInternalServerError("An error occurred while getting Funkwhale status") 

@funkwhale_api_bp.route('/callback/', methods=['GET'])
@crossdomain
@ratelimit()
def funkwhale_callback():
    """Handle the OAuth callback from Funkwhale.
    
    This endpoint is called by Funkwhale after the user authorizes the application.
    It exchanges the authorization code for an access token and creates a new
    Funkwhale connection for the user.
    """
    try:
        # Check for error in callback
        error = request.args.get('error')
        if error:
            current_app.logger.error("Funkwhale OAuth error: %s", error)
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error=f"Funkwhale authorization failed: {error}"))

        # Verify state parameter to prevent CSRF
        state = request.args.get('state')
        if not state:
            current_app.logger.error("No state parameter in callback")
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="Missing state parameter"))
        
        stored_state = session.get('funkwhale_state')
        if not stored_state or state != stored_state:
            current_app.logger.error("Invalid state parameter. Expected: %s, Got: %s", stored_state, state)
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="Invalid state parameter"))
        
        # Get the authorization code
        code = request.args.get('code')
        if not code:
            current_app.logger.error("No authorization code in callback")
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="No authorization code received"))
        
        # Get the host URL from session
        host_url = session.get('funkwhale_host_url')
        if not host_url:
            current_app.logger.error("No host URL in session")
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="No host URL found in session"))
        
        # Get the user ID from session
        user_id = session.get('funkwhale_user_id')
        if not user_id:
            current_app.logger.error("No user ID in session")
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="No user ID found in session"))
        
        # Exchange code for access token
        try:
            service = FunkwhaleService()
            token = service.fetch_access_token(code)
            
            # Get client_id, client_secret, scopes from server
            server = db_funkwhale.get_server_by_host_url(host_url)
            if not server:
                raise ExternalServiceError("No Funkwhale server found for host_url")
            client_id = server['client_id']
            client_secret = server['client_secret']
            scopes = server['scopes']
            
            # Create new Funkwhale connection
            service.add_new_user(user_id, host_url, token, client_id, client_secret, scopes)
            
            # Clear session data
            session.pop('funkwhale_state', None)
            session.pop('funkwhale_host_url', None)
            session.pop('funkwhale_user_id', None)
            
            # Redirect back to music services page with success message
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', success="Successfully connected to Funkwhale"))
        except ExternalServiceError as e:
            current_app.logger.error("Error in FunkwhaleService: %s", str(e))
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error=str(e)))
        except Exception as e:
            current_app.logger.error("Unexpected error in FunkwhaleService: %s", str(e), exc_info=True)
            return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="An unexpected error occurred while connecting to Funkwhale"))

    except Exception as e:
        current_app.logger.error("Error in funkwhale_callback: %s", str(e), exc_info=True)
        return redirect(url_for('settings.music_services_details', _anchor='funkwhale', error="An unexpected error occurred"))

@funkwhale_api_bp.route('/refresh/', methods=['POST'])
@crossdomain
@ratelimit()
def refresh_funkwhale_token():
    """Refresh a user's Funkwhale access token.
    
    The request should contain the following JSON data:
    {
        "host_url": "https://funkwhale.example.com"
    }
    
    Returns:
        A JSON response with the new access token.
    """
    user = validate_auth_header()
    if not user:
        raise APIUnauthorized("You must be logged in to refresh Funkwhale tokens")

    try:
        data = request.get_json()
        if not data or 'host_url' not in data:
            raise APIBadRequest("Missing host_url in request")
        
        host_url = validate_funkwhale_url(data['host_url'])
        
        current_app.logger.info(f"Refresh token request for user {user['id']} at {host_url}")
        
        service = FunkwhaleService()
        user_data = service.get_user(user['id'], host_url)
        if not user_data:
            current_app.logger.warning(f"No Funkwhale connection found for user {user['id']} at {host_url}")
            raise APINotFound("User has not authenticated to Funkwhale at %s" % host_url)
        
        if not user_data.get('refresh_token'):
            current_app.logger.warning(f"No refresh token available for user {user['id']} at {host_url}")
            raise APIBadRequest("No refresh token available for this connection")
        
        # Check if token has expired and refresh if needed
        if service.user_oauth_token_has_expired(user_data):
            current_app.logger.debug(f"Token expired for user {user['id']} at {host_url}, refreshing...")
            try:
                refreshed_user = service.refresh_access_token(
                    user['id'], 
                    host_url, 
                    user_data['refresh_token']
                )
                current_app.logger.info(f"Successfully refreshed Funkwhale token for user {user['id']} at {host_url}")
                user_data = refreshed_user
            except ExternalServiceInvalidGrantError:
                current_app.logger.warning(f"User {user['id']} has revoked authorization to Funkwhale at {host_url}")
                raise APIForbidden("User has revoked authorization to Funkwhale")
            except ExternalServiceError as e:
                # Check if this is an invalid_client error (OAuth app deleted)
                if "invalid_client" in str(e).lower():
                    current_app.logger.warning(f"Invalid client error for user {user['id']} at {host_url} - OAuth app likely deleted")
                    raise APIForbidden("Funkwhale connection is no longer valid - please reconnect to this server")
                current_app.logger.error(f"Funkwhale service error for user {user['id']} at {host_url}: {e}")
                raise APIServiceUnavailable("Cannot refresh Funkwhale token right now")
            except Exception as e:
                current_app.logger.error(f"Unable to refresh Funkwhale token for user {user['id']} at {host_url}: {e}", exc_info=True)
                raise APIServiceUnavailable("Cannot refresh Funkwhale token right now")
        else:
            current_app.logger.debug(f"Token for user {user['id']} at {host_url} is still valid, no refresh needed")
        
        return jsonify({"access_token": user_data["access_token"]})
        
    except (APIBadRequest, APINotFound, APIUnauthorized, APIForbidden, APIServiceUnavailable) as e:
        raise e
    except Exception as e:
        current_app.logger.error("Unexpected error in refresh_funkwhale_token: %s", str(e), exc_info=True)
        raise APIInternalServerError("An error occurred while refreshing Funkwhale token")