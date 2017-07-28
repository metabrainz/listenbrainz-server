from flask import render_template, make_response, jsonify, request
from yattag import Doc
import yattag
import ujson
import collections
from listenbrainz.webserver import API_PREFIX

LastFMError = collections.namedtuple('LastFMError', ['code', 'message'])

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
        resp = make_response(render_template(template, error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, code

    def json_error_wrapper(error, code):
        return jsonify({
            'code': code,
            'error': error.description,
            }), code

    def handle_error(error, code):
        """ Returns appropriate error message on HTTP exceptions

            error (werkzeug.exceptions.HTTPException): The exception that needs to be handled
            code (int): the HTTP error code that should be returned

            Returns:
                A Response which will be a json error if request was made to the LB api and an html page
                otherwise
        """
        if request.path.startswith(API_PREFIX):
            return json_error_wrapper(error, code)
        else:
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
        return handle_error(error, 500)

    @app.errorhandler(503)
    def service_unavailable(error):
        return handle_error(error, 503)

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
