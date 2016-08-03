from flask import render_template, make_response
from yattag import Doc
import yattag
import ujson


# List of errors compatible with LastFM messages for API_compat.
ERROR_MESSAGES = {
    1: "This error does not exist",
    2: "Invalid service -This service does not exist",
    3: "Invalid Method - No method with that name in this package",
    4: "Invalid Token - Invalid authentication token supplied",
    5: "Invalid format - This service doesn't exist in that format",
    6: "Invalid parameters - Your request is missing a required parameter",
    7: "Invalid resource specified",
    8: "Operation failed - Most likely the backend service failed. Please try again.",
    9: "Invalid session key - Please re-authenticate",
    10: "Invalid API key - You must be granted a valid key by last.fm",
    11: "Service Offline - This service is temporarily offline. Try again later.",
    12: "Subscribers Only - This station is only available to paid last.fm subscribers",
    13: "Invalid method signature supplied",
    14: "Unauthorized Token - This token has not been authorized",
    15: "This token has expired",
    16: "The service is temporarily unavailable, please try again.",
    17: "Login: User requires to be logged in",
    18: "Trial Expired - This user has no free radio plays left. Subscription required.",
    19: "This error does not exist",
    20: "Not Enough Content - There is not enough content to play this station",
    21: "Not Enough Members - This group does not have enough members for radio",
    22: "Not Enough Fans - This artist does not have enough fans for for radio",
    23: "Not Enough Neighbours - There are not enough neighbours for radio",
    24: "No Peak Radio - This user is not allowed to listen to radio during peak usage",
    25: "Radio Not Found - Radio station not found",
    26: "API Key Suspended - This application is not allowed to make requests to the web services",
    27: "Deprecated - This type of request is no longer supported",
    29: "Rate Limit Exceded - Your IP has made too many requests in a short period, exceeding our API guidelines"
}

def init_error_handlers(app):

    def error_wrapper(template, error, code):
        resp = make_response(render_template(template, error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, code

    @app.errorhandler(400)
    def bad_request(error):
        return error_wrapper('errors/400.html', error, 400)

    @app.errorhandler(401)
    def unauthorized(error):
        return error_wrapper('errors/401.html', error, 401)

    @app.errorhandler(403)
    def forbidden(error):
        return error_wrapper('errors/403.html', error, 403)

    @app.errorhandler(404)
    def not_found(error):
        return error_wrapper('errors/404.html', error, 404)

    @app.errorhandler(413)
    def file_size_too_large(error):
        return error_wrapper('errors/413.html', error, 413)

    @app.errorhandler(500)
    def internal_server_error(error):
        return error_wrapper('errors/500.html', error, 500)

    @app.errorhandler(503)
    def service_unavailable(error):
        return error_wrapper('errors/503.html', error, 503)

    # Handle error of API_compat
    @app.errorhandler(InvalidAPIUsage)
    def handle_api_compat_error(error):
        return error.render_error()



class InvalidAPIUsage(Exception):
    """ General error class for the API_compat to render errors in multiple formats """
    def __init__(self, api_error_code, status_code=500, output_format="xml"):
        Exception.__init__(self)
        self.api_error_code = api_error_code
        self.status_code = status_code
        self.output_format = output_format

    def render_error(self):
        return {
            "json": self.to_json,
            "xml": self.to_xml
        }.get(self.output_format, self.to_xml)()

    def to_json(self):
        return ujson.dumps({
            "error": self.api_error_code,
            "message": ERROR_MESSAGES[self.api_error_code]
        }, indent=4)

    def to_xml(self):
        doc, tag, text = Doc().tagtext()
        with tag('lfm', status="failed"):
            with tag('error', code=self.api_error_code):
                text(ERROR_MESSAGES[self.api_error_code])
        return '<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue())
