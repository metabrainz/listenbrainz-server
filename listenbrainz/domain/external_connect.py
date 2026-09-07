""" Support for third party applications that want their users to connect an external
music service to ListenBrainz. Only Spotify is offered for now, see CONNECTABLE_SERVICES.

OAuth requires the session state protecting the authorization request to be created on the
same domain that initiates it, so a partner application cannot start the flow on our behalf.
Instead the partner sends the user to ListenBrainz, ListenBrainz creates the session state
and runs the entire OAuth dance with the music service, stores the resulting tokens and
finally sends the user back to the partner application.

The partner has to know which MetaBrainz account the user has before it can start the flow,
which it proves by sending us a MetaBrainz OAuth access token the user granted it:

1. the partner posts the access token to ``/connect/<service>/`` from its backend.
   ListenBrainz introspects the token, checks that it carries the
   ``listenbrainz:connect-services`` scope, looks up the name of the application it was
   issued to in the MetaBrainz OAuth client registry and hands back a single use url. The
   user is never logged in to ListenBrainz, neither here nor anywhere else in the flow.
2. the partner sends the user's browser to that url. ListenBrainz shows a confirmation page
   naming the partner and the ListenBrainz account the music service would be connected to.
3. the user confirms. ListenBrainz generates the OAuth state, remembers the request in the
   user's session and redirects the user to the music service
4. the user authorizes ListenBrainz on the music service
5. the music service redirects back to the usual ListenBrainz callback, which stores the
   tokens
6. ListenBrainz redirects the user back to ``redirect_uri`` with ``status`` (and ``error``
   if the flow failed) plus the ``state`` the partner sent when it started the flow

The confirmation page in step 2 is what keeps the ticket from being a bearer capability that
silently says "whoever opens this link is user U". Nothing else in the flow ever asks the
person in front of the browser whether that is true: they are not logged in to ListenBrainz,
and the authorization screen they see afterwards belongs to the music service and only names
ListenBrainz. Without the confirmation, anybody able to mint a ticket could mint one for
their own account, send the link to somebody else and end up with that person's music
service connected to the attacker's ListenBrainz account.
"""

import base64
import os
import secrets
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from brainzutils import cache
from flask import current_app, session, url_for

import listenbrainz.db.oauth_client as db_oauth_client
import listenbrainz.db.user as db_user
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.soundcloud import SoundCloudService
from listenbrainz.domain.spotify import SPOTIFY_IMPORT_PERMISSIONS, SPOTIFY_LISTEN_PERMISSIONS
from listenbrainz.webserver import db_conn, meb_conn

# the key under which the in-progress request is stored in the user's ListenBrainz session
SESSION_KEY = "external_connect_request"

# the key under which the confirmation page remembers what it was shown for, see
# start_confirmation
CONFIRM_SESSION_KEY = "external_connect_confirm"

# the prefix of the keys under which the OAuth state of an authorization started from the
# ListenBrainz settings page is stored in the user's session, see settings_oauth_state_key
SETTINGS_OAUTH_STATE_SESSION_KEY_PREFIX = "music_service_oauth_state"

# an authorization the user does not finish within this duration is abandoned
REQUEST_TTL = timedelta(minutes=30)

# the partner state is stored in the (cookie backed) session and echoed back verbatim, so
# cap it to keep the session cookie small
MAX_CLIENT_STATE_LENGTH = 255

# the scope a MetaBrainz OAuth access token must carry for a partner application to be
# allowed to connect music services on behalf of its owner
CONNECT_SERVICES_SCOPE = "listenbrainz:connect-services"

# MetaBrainz OAuth access tokens are prefixed with this, ListenBrainz user tokens are not
METABRAINZ_TOKEN_PREFIX = "meba_"

# how long the partner has to send the user to the url returned by the token endpoint. It
# is only the time between the partner's backend call and the browser redirect, so it can
# be short.
TICKET_TTL = timedelta(minutes=10)
TICKET_CACHE_NAMESPACE = "external_connect_ticket"

# values of the error parameter ListenBrainz sends back to the partner application
ERROR_INVALID_REQUEST = "invalid_request"
ERROR_ACCESS_DENIED = "access_denied"
ERROR_EMAIL_REQUIRED = "email_required"
ERROR_EXPIRED_REQUEST = "expired_request"
ERROR_SERVER_ERROR = "server_error"

STATUS_CONNECTED = "connected"
STATUS_ERROR = "error"

# Query parameters whose values are owned by this flow. A partner may include unrelated
# parameters in its redirect URI, but these must be replaced rather than duplicated when
# the result is returned.
RETURN_QUERY_PARAMETERS = {"service", "status", "error", "error_description", "state"}


@dataclass(frozen=True)
class ConnectableService:
    """ A music service that can be connected through a pure browser redirect OAuth flow.

    Only Spotify is offered for now. Adding SoundCloud or CritiqueBrainz is a matter of
    listing them below, everything else in this module is service agnostic. Services needing
    input from the user before the authorization request can be made (a Funkwhale instance
    url, a Last.fm username, Navidrome credentials) or needing javascript on a ListenBrainz
    page (Apple Music) cannot be part of this flow at all.

    Args:
        name: the name of the service, as used in urls
        permissions: maps the permission names a partner may ask for to the OAuth scopes
            they translate to. The names match the ones used by the ListenBrainz settings
            page so that both flows stay consistent.
        default_permission: the permission used when the partner does not ask for one
        label: the name of the service as shown to the user
        permission_descriptions: what each permission lets ListenBrainz do, in words the
            user can act on. Shown on the confirmation page.
    """
    name: str
    permissions: dict[str, frozenset[str]]
    default_permission: str
    label: str
    permission_descriptions: dict[str, str]

    def describe_permission(self, permission: str) -> str:
        return self.permission_descriptions.get(permission, f"access your {self.label} account")


CONNECTABLE_SERVICES = {
    service.name: service
    for service in [
        ConnectableService(
            name="spotify",
            permissions={
                "import": frozenset(SPOTIFY_IMPORT_PERMISSIONS),
                "listen": frozenset(SPOTIFY_LISTEN_PERMISSIONS),
                "both": frozenset(SPOTIFY_IMPORT_PERMISSIONS | SPOTIFY_LISTEN_PERMISSIONS),
            },
            default_permission="import",
            label="Spotify",
            permission_descriptions={
                "import": "read your Spotify listening history",
                "listen": "play music from Spotify in the ListenBrainz player",
                "both": "read your Spotify listening history and play music from Spotify in"
                        " the ListenBrainz player",
            },
        ),
    ]
}


@dataclass
class ExternalConnectRequest:
    """ An in-progress request by a partner application to connect a music service. """
    redirect_uri: str
    service: str
    permission: str
    oauth_state: str
    client_state: Optional[str] = None
    # the name the application the access token was issued to is registered under with
    # MetaBrainz, if we could look it up. Only used to name it on the confirmation page.
    client_name: Optional[str] = None
    # the ListenBrainz user the music service is connected for. It is set as soon as we know
    # who the user is, either from the access token the partner sent us or from the session
    # of the logged in user.
    user_id: Optional[int] = None
    # whether to send the user to the music service even if the account is already connected
    # with the requested permissions
    force: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def has_expired(self) -> bool:
        try:
            created_at = datetime.fromisoformat(self.created_at)
        except (TypeError, ValueError):
            return True
        return datetime.now(timezone.utc) - created_at > REQUEST_TTL

    def redirect_host(self) -> str:
        """ The host the user will be sent back to, shown on the confirmation page. """
        return urlparse(self.redirect_uri).netloc

    def describe_client(self) -> str:
        """ How the application is named to the user on the confirmation page.

        The registered name is what the user is likely to recognise, but it is chosen by
        the application's owner, so the host they are going to be returned to is shown
        alongside it. When there is no name to be had, the host stands on its own.
        """
        if self.client_name:
            return f"{self.client_name} ({self.redirect_host()})"
        return self.redirect_host()


class ExternalConnectValidationError(Exception):
    """ Raised when a partner request is malformed in a way that stops us from redirecting
    the user back to the partner application. """
    pass


class ExternalConnectAuthError(Exception):
    """ Raised when the access token a partner application sent us does not allow it to
    connect music services for its owner. """
    pass


def _get_string(args, key: str) -> Optional[str]:
    """ Return a value a partner application sent us that has to be a string, if any.

    The values come straight out of a json body, so anything could be in there.
    """
    value = args.get(key)
    if value is None or isinstance(value, str):
        return value
    raise ExternalConnectValidationError(f"{key} must be a string.")


def settings_oauth_state_key(service_name: str) -> str:
    """ Return the session key holding the OAuth state of an authorization the user started
    from the ListenBrainz settings page.

    There is one key per service so that a user connecting two services at the same time
    does not have the second authorization clobber the state of the first one.
    """
    return f"{SETTINGS_OAUTH_STATE_SESSION_KEY_PREFIX}_{service_name.lower()}"


def get_connectable_service(service_name: str) -> Optional[ConnectableService]:
    """ Return the service with the given name if it can be connected by a partner app. """
    return CONNECTABLE_SERVICES.get(service_name.lower())


def validate_redirect_uri(redirect_uri: Optional[str]) -> str:
    """ Check the url a partner application wants the user sent back to.

    There is no registry of partner applications, so there is no allow list to match this
    against: the access token is what says the caller is allowed to be here at all. All we
    can do is make sure it is an absolute url the browser can be redirected to, so that this
    endpoint cannot be pointed at a javascript: or data: url.

    Raises:
        ExternalConnectValidationError: if it is missing or not such a url.
    """
    if not redirect_uri:
        raise ExternalConnectValidationError("Missing redirect_uri.")

    parsed = urlparse(redirect_uri)
    if not parsed.netloc or parsed.scheme not in ("http", "https"):
        raise ExternalConnectValidationError("redirect_uri must be an absolute http or https url.")
    # a partner running on localhost is developing against us, everybody else is sending a
    # user's browser across the internet and has no excuse for doing it in the clear
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ExternalConnectValidationError("redirect_uri must use https.")
    return redirect_uri


def resolve_token(access_token: Optional[str]) -> tuple[dict, dict]:
    """ Return the ListenBrainz user a MetaBrainz OAuth access token was issued for, along
    with the introspection response it came from.

    Only MetaBrainz OAuth access tokens carrying the connect services scope are accepted.
    ListenBrainz user tokens are deliberately not accepted here because connecting a music
    service on someone's behalf is something the user has to grant explicitly.

    Raises:
        ExternalConnectAuthError: if the token is missing, invalid, expired, lacks the scope
            or belongs to somebody without a ListenBrainz account.
        requests.RequestException: if the introspection endpoint could not be reached.
    """
    if not access_token or not access_token.startswith(METABRAINZ_TOKEN_PREFIX):
        raise ExternalConnectAuthError("A MetaBrainz OAuth access token is required.")

    token = MusicBrainzService().get_user_info(access_token)

    if not token.get("active"):
        raise ExternalConnectAuthError("Invalid access token.")

    expires_at = token.get("expires_at")
    if expires_at is not None and datetime.fromtimestamp(expires_at, timezone.utc) < datetime.now(timezone.utc):
        raise ExternalConnectAuthError("Invalid access token.")

    scopes = token.get("scope") or []
    if isinstance(scopes, str):
        # Accept the space-delimited representation too, since older introspection
        # implementations and test doubles may still return it.
        scopes = scopes.split()
    if not isinstance(scopes, list) or CONNECT_SERVICES_SCOPE not in scopes:
        raise ExternalConnectAuthError(f"The access token needs the {CONNECT_SERVICES_SCOPE} scope.")

    user = _get_user_from_introspection(token)
    if user is None:
        raise ExternalConnectAuthError("The owner of the access token does not have a ListenBrainz account.")
    return user, token


def get_client_name(client_id: Optional[str]) -> Optional[str]:
    """ Return the name the application an access token was issued to is registered under.

    The registry is MetaBrainz's, so this needs the MetaBrainz database. It is only used to
    put a name on the confirmation page, so a deployment without that database configured
    (or a hiccup reaching it) falls back to naming the application by the host the user is
    going to be sent back to rather than failing the flow.
    """
    # meb_conn is a proxy around a connection that only exists when the MetaBrainz database
    # is configured, so the config is what has to be checked, not the proxy
    if not client_id or not current_app.config.get("SQLALCHEMY_METABRAINZ_URI"):
        return None
    try:
        return db_oauth_client.get_client_name(meb_conn, client_id)
    except Exception:
        current_app.logger.error("Could not look up the name of OAuth client %s:", client_id, exc_info=True)
        return None


def _get_user_from_introspection(token: dict) -> Optional[dict]:
    """ Look up the ListenBrainz user an introspected access token belongs to.

    The introspection response identifies the user by their MusicBrainz row id in ``sub``,
    with their MusicBrainz username in ``username`` used as a fallback for the accounts we
    do not have a row id for yet. A token issued through the client credentials grant has no
    user behind it at all and carries the sentinel ``-1``.
    """
    try:
        musicbrainz_row_id = int(token.get("sub"))
    except (TypeError, ValueError):
        return None
    if musicbrainz_row_id < 0:
        return None
    return db_user.get_by_mb_row_id(db_conn, musicbrainz_row_id,
                                    musicbrainz_id=token.get("username"), fetch_email=True)


def create_ticket(connect_request: ExternalConnectRequest) -> str:
    """ Store a validated request and return the single use ticket identifying it.

    The ticket is what lets the user's browser start the authorization without logging in to
    ListenBrainz, so it is stored server side and can only be used once.
    """
    ticket = secrets.token_urlsafe(32)
    cache.set(ticket, asdict(connect_request), int(TICKET_TTL.total_seconds()),
              namespace=TICKET_CACHE_NAMESPACE)
    return ticket


def _load_ticket(ticket: Optional[str], service_name: str) -> Optional[ExternalConnectRequest]:
    if not ticket:
        return None

    stored = cache.get(ticket, namespace=TICKET_CACHE_NAMESPACE)
    if not stored:
        return None

    try:
        connect_request = ExternalConnectRequest(**stored)
    except TypeError:
        return None
    return connect_request if connect_request.service == service_name.lower() else None


def peek_ticket(ticket: Optional[str], service_name: str) -> Optional[ExternalConnectRequest]:
    """ Return the request a ticket was created for without spending the ticket.

    This is what the confirmation page is rendered from. The ticket is only spent once the
    user confirms, so reloading the page or going back to it does not lose the request.
    """
    return _load_ticket(ticket, service_name)


def consume_ticket(ticket: Optional[str], service_name: str) -> Optional[ExternalConnectRequest]:
    """ Return the request a ticket was created for and invalidate the ticket. """
    connect_request = _load_ticket(ticket, service_name)
    if connect_request is None:
        return None

    # deleting the ticket is what makes it single use, only carry on if this request is the
    # one that actually removed it
    if cache.delete(ticket, namespace=TICKET_CACHE_NAMESPACE) != 1:
        return None
    return connect_request


def start_confirmation(ticket: str) -> str:
    """ Remember that this browser was served the confirmation page for the given ticket and
    return the nonce the confirmation has to be submitted with.

    The nonce is what stops the partner application from submitting the confirmation itself:
    it is only ever written into the page handed to the browser that asked for it and into a
    cookie, neither of which the partner can read.
    """
    nonce = secrets.token_urlsafe(32)
    session[CONFIRM_SESSION_KEY] = {"ticket": ticket, "nonce": nonce}
    return nonce


def check_confirmation(ticket: Optional[str], nonce: Optional[str]) -> bool:
    """ Check that this browser was served the confirmation page for the given ticket. """
    stored = session.pop(CONFIRM_SESSION_KEY, None)
    if not isinstance(stored, dict) or not ticket or not nonce:
        return False
    return (secrets.compare_digest(stored.get("ticket") or "", ticket)
            and secrets.compare_digest(stored.get("nonce") or "", nonce))


def build_ticket_url(connect_request: ExternalConnectRequest, ticket: str) -> str:
    """ Return the url the partner application has to send the user's browser to. """
    return url_for("external_connect.connect", service_name=connect_request.service,
                   ticket=ticket, _external=True)


def validate_request_args(service_name: str, args) -> ExternalConnectRequest:
    """ Validate what a partner application sent us and turn it into an
    :class:`ExternalConnectRequest`.

    The returned request has no user attached and has not been stored anywhere yet, see
    :func:`create_ticket`.

    Args:
        service_name: the music service the user wants to connect
        args: the json body of the incoming request

    Raises:
        ExternalConnectValidationError: if anything about the request is invalid.
    """
    connectable = get_connectable_service(service_name)
    if connectable is None:
        raise ExternalConnectValidationError(f"{service_name} cannot be connected from another application.")

    redirect_uri = validate_redirect_uri(_get_string(args, "redirect_uri"))

    client_state = _get_string(args, "state")
    if client_state is not None and len(client_state) > MAX_CLIENT_STATE_LENGTH:
        raise ExternalConnectValidationError(
            f"state cannot be longer than {MAX_CLIENT_STATE_LENGTH} characters."
        )

    permission = _get_string(args, "permissions") or connectable.default_permission
    if permission not in connectable.permissions:
        raise ExternalConnectValidationError(
            f"'{permission}' is not a valid value of permissions for {connectable.name}, "
            f"use one of: {', '.join(sorted(connectable.permissions))}."
        )

    return ExternalConnectRequest(
        redirect_uri=redirect_uri,
        service=connectable.name,
        permission=permission,
        oauth_state=base64.b64encode(os.urandom(32)).decode("utf-8"),
        client_state=client_state,
    )


def store_request(connect_request: ExternalConnectRequest):
    """ Remember the in-progress request for the duration of the OAuth dance. """
    session[SESSION_KEY] = asdict(connect_request)
    # this authorization is tracked by the stored request, drop the state of any
    # authorization of the same service the user started from the settings page
    session.pop(settings_oauth_state_key(connect_request.service), None)


def get_request(service_name: str) -> Optional[ExternalConnectRequest]:
    """ Return the in-progress request for the given service without forgetting it.

    The callback has to inspect the request to find the expected OAuth state, but must not
    consume it until that state has been validated. Otherwise an unrelated request to the
    callback could cancel a real authorization that is still in flight.
    """
    stored = session.get(SESSION_KEY)
    if not stored:
        return None

    try:
        connect_request = ExternalConnectRequest(**stored)
    except TypeError:
        session.pop(SESSION_KEY, None)
        return None

    if connect_request.service != service_name.lower():
        return None

    return connect_request


def pop_request(service_name: str) -> Optional[ExternalConnectRequest]:
    """ Return and forget the in-progress request for the given service, if any. """
    connect_request = get_request(service_name)
    if connect_request is None:
        return None

    session.pop(SESSION_KEY, None)
    return connect_request


def build_return_url(connect_request: ExternalConnectRequest, error: Optional[str] = None,
                     error_description: Optional[str] = None) -> str:
    """ Build the url to send the user back to once the flow has finished.

    Args:
        connect_request: the request the partner application started
        error: the error that made the flow fail, if it did
        error_description: a human readable description of the error
    """
    params = [
        ("service", connect_request.service),
        ("status", STATUS_ERROR if error else STATUS_CONNECTED),
    ]
    if error:
        params.append(("error", error))
    if error_description:
        params.append(("error_description", error_description))
    if connect_request.client_state is not None:
        params.append(("state", connect_request.client_state))

    parsed = urlparse(connect_request.redirect_uri)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in RETURN_QUERY_PARAMETERS
    ] + params
    return urlunparse(parsed._replace(query=urlencode(query)))


def build_authorize_url(service, permissions, state: str) -> str:
    """ Build the url of the music service the user has to be sent to for authorizing us.

    Also stores whatever else the callback will need to complete the authorization, for
    instance the PKCE code verifier for SoundCloud.

    Args:
        service: the :class:`~listenbrainz.domain.external_service.ExternalService` instance
        permissions: the OAuth scopes to ask the service for
        state: the OAuth state protecting the authorization request
    """
    if isinstance(service, SoundCloudService):
        code_verifier, code_challenge = SoundCloudService.generate_pkce_pair()
        session["soundcloud_code_verifier"] = code_verifier
        return service.get_authorize_url(
            list(permissions),
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )
    return service.get_authorize_url(list(permissions), state=state)
