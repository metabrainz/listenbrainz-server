""" Entry points of the flow that lets a third party application send a user to ListenBrainz
to connect an external music service. See :mod:`listenbrainz.domain.external_connect` for a
description of the whole flow.
"""

import requests
from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from flask_login import current_user
from werkzeug.exceptions import BadRequest

import listenbrainz.db.user as db_user
from listenbrainz.domain import external_connect
from listenbrainz.domain.external_connect import ExternalConnectAuthError, ExternalConnectValidationError
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.errors import APIBadRequest, APIServiceUnavailable, APIUnauthorized
from listenbrainz.webserver.utils import CONNECT_SERVICES_WITHOUT_EMAIL_ERROR
from listenbrainz.webserver.views.settings import _get_service_or_raise_404, _user_has_verified_email, \
    _user_id_has_verified_email

external_connect_bp = Blueprint("external_connect", __name__)

# shown when the ticket a browser arrives with is unknown, expired or already spent
STALE_TICKET_ERROR = "This link has already been used or has expired, please start again."


@external_connect_bp.post("/<service_name>/")
def create_connect_session(service_name: str):
    """ Start connecting a music service for the owner of a MetaBrainz OAuth access token.

    This is meant to be called by the backend of a partner application that already knows
    which MetaBrainz account the user has. It does not involve the user's browser, so it
    cannot redirect them anywhere. Instead it returns a single use url the partner has to
    send the user's browser to, which is where the user confirms the account and the
    redirect to the music service happens, see :func:`connect`.

    The access token is read from the Authorization header and has to be a MetaBrainz OAuth
    access token carrying the ``listenbrainz:connect-services`` scope. That scope is only
    granted to applications MetaBrainz has approved for it, so it is the whole of the
    authorization here: ListenBrainz keeps no registry of partner applications of its own.

    JSON body:
        redirect_uri: **(required)** where to send the user once the flow finishes, see
            :func:`connect`.
        state: an opaque value returned unchanged to the partner application.
        permissions: what the partner wants ListenBrainz to be able to do with the account.
        force: set to true to always send the user through the authorization screen of the
            music service even if the account is already connected.

    Returns:
        ``{"url": ..., "expires_in": ...}`` where url is the single use url to send the
        user's browser to and expires_in is how long it stays valid, in seconds.
    """
    access_token = _get_access_token()

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise APIBadRequest("The request body must be a json object.")

    try:
        connect_request = external_connect.validate_request_args(service_name, data)
    except ExternalConnectValidationError as error:
        raise APIBadRequest(str(error))

    try:
        user, token = external_connect.resolve_token(access_token)
    except ExternalConnectAuthError as error:
        raise APIUnauthorized(str(error))
    except requests.RequestException:
        current_app.logger.error("Error while introspecting access token:", exc_info=True)
        raise APIServiceUnavailable("Something went wrong. Please try again later.")

    if not _user_has_verified_email(user):
        raise APIUnauthorized(CONNECT_SERVICES_WITHOUT_EMAIL_ERROR)

    connect_request.user_id = user["id"]
    connect_request.client_name = external_connect.get_client_name(token.get("client_id"))
    if _is_true(data.get("force")):
        connect_request.force = True

    ticket = external_connect.create_ticket(connect_request)
    return jsonify({
        "url": external_connect.build_ticket_url(connect_request, ticket),
        "expires_in": int(external_connect.TICKET_TTL.total_seconds()),
    })


@external_connect_bp.get("/<service_name>/")
def connect(service_name: str):
    """ Ask the user to confirm the ListenBrainz account before starting the authorization.

    This is the url :func:`create_connect_session` returns and the partner application has
    to send the user's browser to. The request it belongs to was already validated when the
    ticket was created, so the ticket is the only query argument that is read.

    The page it renders is the only point in the flow where the person in front of the
    browser is told which ListenBrainz account the music service is about to be connected
    to. They are not logged in to ListenBrainz, and the authorization screen the music
    service shows afterwards only names ListenBrainz, so without this page a ticket minted
    for one account could be handed to somebody else's browser unnoticed.

    Query arguments:
        ticket: **(required)** the single use ticket obtained from the token endpoint.
    """
    ticket = request.args.get("ticket")
    connect_request = external_connect.peek_ticket(ticket, service_name)
    if connect_request is None:
        raise BadRequest(STALE_TICKET_ERROR)

    wrong_user = _reject_wrong_user(connect_request)
    if wrong_user is not None:
        return wrong_user

    user = db_user.get(db_conn, connect_request.user_id)
    if user is None:
        current_app.logger.error("External connect ticket for unknown user %s", connect_request.user_id)
        return _return_to_client(
            connect_request, external_connect.ERROR_SERVER_ERROR,
            "The ListenBrainz account this link was created for no longer exists."
        )

    connectable = external_connect.get_connectable_service(connect_request.service)
    return render_template(
        "external_connect/confirm.html",
        connect_request=connect_request,
        ticket=ticket,
        nonce=external_connect.start_confirmation(ticket),
        musicbrainz_id=user["musicbrainz_id"],
        service_label=connectable.label,
        permission_description=connectable.describe_permission(connect_request.permission),
        hide_navbar_user_menu=True,
    )


@external_connect_bp.post("/<service_name>/confirm/")
def confirm(service_name: str):
    """ Act on the confirmation page: start the authorization or send the user back.

    The nonce has to be the one :func:`connect` put into the page it served this browser.
    Without it the partner application could post this form itself and skip the page it is
    supposed to show the user, which is the whole point of the confirmation.
    """
    ticket = request.form.get("ticket")
    if not external_connect.check_confirmation(ticket, request.form.get("nonce")):
        raise BadRequest("Please open the connect link again to confirm.")

    connect_request = external_connect.consume_ticket(ticket, service_name)
    if connect_request is None:
        raise BadRequest(STALE_TICKET_ERROR)

    wrong_user = _reject_wrong_user(connect_request)
    if wrong_user is not None:
        return wrong_user

    if request.form.get("action") != "continue":
        return _return_to_client(
            connect_request, external_connect.ERROR_ACCESS_DENIED,
            "The user did not confirm the ListenBrainz account."
        )

    return _authorize(connect_request)


def _reject_wrong_user(connect_request):
    """ Refuse a request whose account is not the one this browser is logged in as, if any.

    Being logged in is not required anywhere in this flow, but when the browser does have a
    ListenBrainz session we know for a fact who is using it, so a mismatch is an answer and
    not a question to put to the user.
    """
    if not current_user.is_authenticated or current_user.id == connect_request.user_id:
        return None
    current_app.logger.error("%s connect link for user %s opened by user %s",
                             connect_request.service, connect_request.user_id, current_user.id)
    return _return_to_client(
        connect_request, external_connect.ERROR_INVALID_REQUEST,
        "This link was not created for the current ListenBrainz user."
    )


def _authorize(connect_request):
    """ Redirect the user to the music service to authorize a validated request. """
    connectable = external_connect.get_connectable_service(connect_request.service)
    permissions = connectable.permissions[connect_request.permission]

    if not _user_id_has_verified_email(connect_request.user_id):
        return _return_to_client(
            connect_request, external_connect.ERROR_EMAIL_REQUIRED, CONNECT_SERVICES_WITHOUT_EMAIL_ERROR
        )

    service = _get_service_or_raise_404(connectable.name)

    existing_user = service.get_user(connect_request.user_id)
    has_requested_permissions = bool(existing_user) and set(existing_user.get("scopes") or []) >= permissions
    # nothing to do if the user already gave us everything the partner asked for
    if has_requested_permissions and not connect_request.force:
        return _return_to_client(connect_request)

    try:
        authorize_url = external_connect.build_authorize_url(service, permissions, connect_request.oauth_state)
    except Exception:
        current_app.logger.error("Could not build the %s authorize url for user %s:",
                                 connectable.name, connect_request.user_id, exc_info=True)
        return _return_to_client(
            connect_request, external_connect.ERROR_SERVER_ERROR,
            f"Could not start the {connectable.name} authorization."
        )

    external_connect.store_request(connect_request)
    return redirect(authorize_url)


def _return_to_client(connect_request, error: str = None, error_description: str = None):
    return redirect(external_connect.build_return_url(connect_request, error, error_description))


def _get_access_token():
    """ Return the access token from the Authorization header of the current request. """
    header = request.headers.get("Authorization")
    if not header:
        raise APIUnauthorized("You need to provide an Authorization header.")
    parts = header.split(" ")
    if len(parts) != 2:
        raise APIUnauthorized("Provided Authorization header is invalid.")
    return parts[1]


def _is_true(value) -> bool:
    return str(value).lower() in {"true", "1"}
