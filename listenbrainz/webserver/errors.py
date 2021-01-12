from flask import render_template, make_response, jsonify, request, has_request_context, _request_ctx_stack, current_app
from yattag import Doc
import yattag
import ujson
import collections

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver import API_PREFIX

LastFMError = collections.namedtuple('LastFMError', ['code', 'message'])


class APIError(Exception):
    def __init__(self, message, status_code, payload=None):
        super(APIError, self).__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['code'] = self.status_code
        rv['error'] = self.message
        return rv

    def __str__(self):
        return self.message


class APINoContent(APIError):
    def __init__(self, message, payload=None):
        super(APINoContent, self).__init__(message, 204, payload)


class APINotFound(APIError):
    def __init__(self, message, payload=None):
        super(APINotFound, self).__init__(message, 404, payload)


class APIUnauthorized(APIError):
    def __init__(self, message, payload=None):
        super(APIUnauthorized, self).__init__(message, 401, payload)


class APIBadRequest(APIError):
    def __init__(self, message, payload=None):
        super(APIBadRequest, self).__init__(message, 400, payload)


class APIInternalServerError(APIError):
    def __init__(self, message, payload=None):
        super(APIInternalServerError, self).__init__(message, 500, payload)


class APIServiceUnavailable(APIError):
    def __init__(self, message, payload=None):
        super(APIServiceUnavailable, self).__init__(message, 503, payload)


class APIForbidden(APIError):
    def __init__(self, message, payload=None):
        super(APIForbidden, self).__init__(message, 403, payload)


# List of errors compatible with LastFM messages for API_compat.
class CompatError(object):
    DOES_NOT_EXIST           = LastFMError(code = 1, message = "This error does not exist")
    INVALID_SERVICE          = LastFMError(code = 2, message = "Invalid service -This service does not exist")
    INVALID_METHOD           = LastFMError(code = 3, message = "Invalid Method - No method with that name in this package")
    INVALID_TOKEN            = LastFMError(code = 4, message = "Invalid Token - Invalid authentication token supplied")
    INVALID_FORMAT           = LastFMError(code = 5, message = "Invalid format - This service doesn't exist in that format")
    INVALID_PARAMETERS       = LastFMError(code = 6, message = "Invalid parameters - " \
                                                               "Your request is missing a required parameter")
    INVALID_RESOURCE         = LastFMError(code = 7, message = "Invalid resource specified")
    OP_FAILED                = LastFMError(code = 8, message = "Operation failed - Most likely the backend service failed. " \
                                                               "Please try again.")
    INVALID_SESSION_KEY      = LastFMError(code = 9, message = "Invalid session key - Please re-authenticate")
    INVALID_API_KEY          = LastFMError(code = 10, message = "Invalid API key - You must be granted a valid key by last.fm")
    SERVICE_OFFLINE          = LastFMError(code = 11, message = "Service Offline - This service is temporarily offline. " \
                                                                "Try again later.")
    SUBSCRIBERS_ONLY         = LastFMError(code = 12, message = "Subscribers Only - This station is only available to " \
                                                                "paid last.fm subscribers")
    INVALID_METHOD_SIGNATURE = LastFMError(code = 13, message = "Invalid method signature supplied")
    UNAUTHORIZED_TOKEN       = LastFMError(code = 14, message = "Unauthorized Token - This token has not been authorized")
    TOKEN_EXPIRED            = LastFMError(code = 15, message = "This token has expired")
    SERVICE_UNAVAILABLE      = LastFMError(code = 16, message = "The service is temporarily unavailable, please try again.")
    NEED_LOGIN               = LastFMError(code = 17, message = "Login: User requires to be logged in")
    TRIAL_EXPIRED            = LastFMError(code = 18, message = "Trial Expired - This user has no free radio plays left. " \
                                                                "Subscription required.")
    DOES_NOT_EXIST_19        = LastFMError(code = 19, message = "This error does not exist")
    NOT_ENOUGH_CONTENT       = LastFMError(code = 20, message = "Not Enough Content - There is not enough content to " \
                                                                "play this station")
    NOT_ENOUGH_MEMBERS       = LastFMError(code = 21, message = "Not Enough Members - This group does not have enough members " \
                                                                "for radio")
    NOT_ENOUGH_FANS          = LastFMError(code = 22, message = "Not Enough Fans - This artist does not have enough fans " \
                                                                "for radio")
    NOT_ENOUGH_NEIGHBOURS    = LastFMError(code = 23, message = "Not Enough Neighbours - There are not enough neighbours " \
                                                                "for radio")
    NO_PEAK_RADIO            = LastFMError(code = 24, message = "No Peak Radio - This user is not allowed to listen to " \
                                                                "radio during peak usage")
    RADIO_NOT_FOUND          = LastFMError(code = 25, message = "Radio Not Found - Radio station not found")
    API_KEY_SUSPENDED        = LastFMError(code = 26, message = "API Key Suspended - This application is not allowed to make "
                                                                "requests to the web services")
    DEPRECATED               = LastFMError(code = 27, message = "Deprecated - This type of request is no longer supported")
    RATE_LIMIT_EXCEEDED      = LastFMError(code = 29, message = "Rate Limit Exceded - Your IP has made too many requests in " \
                                                                "exceeding our API guidelines")


def init_error_handlers(app):
    def error_wrapper(template, error, code):
        hide_navbar_user_menu = False
        if code == 500:
            # On an HTTP500 page we want to make sure we don't do any more database queries
            # in case the error was caused by an un-rolled-back database exception.
            # flask-login will do a query to add `current_user` to the template if it's not
            # already in the request context, so we override it with AnonymousUser to prevent it from doing so
            # Ideally we wouldn't do this, and we would catch and roll back all database exceptions
            if has_request_context() and not hasattr(_request_ctx_stack.top, 'user'):
                _request_ctx_stack.top.user = current_app.login_manager.anonymous_user()
            hide_navbar_user_menu = True

        resp = make_response(render_template(template,
                                             error=error,
                                             hide_navbar_user_menu=hide_navbar_user_menu))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, code

    def handle_error(error, code):
        """ Returns appropriate error message on HTTP exceptions

            error (werkzeug.exceptions.HTTPException): The exception that needs to be handled
            code (int): the HTTP error code that should be returned

            Returns:
                A Response which will be a json error if request was made to the LB api and an html page
                otherwise
        """
        if current_app.config.get('IS_API_COMPAT_APP') or request.path.startswith(API_PREFIX):
            return jsonify({'code': code, 'error': error.description}), code
        return error_wrapper('errors/{code}.html'.format(code=code), error, code)

    @app.errorhandler(400)
    def bad_request(error):
        return handle_error(error, 400)

    @app.errorhandler(401)
    def unauthorized(error):
        return handle_error(error, 401)

    @app.errorhandler(403)
    def forbidden(error):
        return handle_error(error, 403)

    @app.errorhandler(404)
    def not_found(error):
        return handle_error(error, 404)

    @app.errorhandler(413)
    def file_size_too_large(error):
        return handle_error(error, 413)

    @app.errorhandler(500)
    def internal_server_error(error):
        if request.path.startswith(API_PREFIX):
            error = APIError("An unknown error occured.", 500)
            return jsonify(error.to_dict()), error.status_code
        else:
            return handle_error(error, 500)

    @app.errorhandler(502)
    def bad_gateway(error):
        return handle_error(error, 502)

    @app.errorhandler(503)
    def service_unavailable(error):
        return handle_error(error, 503)

    @app.errorhandler(504)
    def gateway_timeout(error):
        return handle_error(error, 504)

    @app.errorhandler(APIError)
    @crossdomain()
    def api_error(error):
        return jsonify(error.to_dict()), error.status_code

    # Handle error of API_compat
    @app.errorhandler(InvalidAPIUsage)
    def handle_api_compat_error(error):
        return error.render_error()


class InvalidAPIUsage(Exception):
    """ General error class for the API_compat to render errors in multiple formats """

    def __init__(self, api_error, status_code=500, output_format="xml"):
        Exception.__init__(self)
        self.api_error = api_error
        self.status_code = status_code
        self.output_format = output_format

    def render_error(self):
        return {
            "json": self.to_json,
            "xml": self.to_xml
        }.get(self.output_format, self.to_xml)()

    def to_json(self):
        return ujson.dumps({
            "error": self.api_error.code,
            "message": self.api_error.message
        }, indent=4)

    def to_xml(self):
        doc, tag, text = Doc().tagtext()
        with tag('lfm', status="failed"):
            with tag('error', code=self.api_error.code):
                text(self.api_error.message)
        return '<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue())
