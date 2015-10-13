from flask import render_template, make_response, jsonify
import webserver.exceptions


def init_error_handlers(app):

    def error_wrapper(template, error, code):
        resp = make_response(render_template(template, error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, code

    @app.errorhandler(webserver.exceptions.APIError)
    def api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

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

    @app.errorhandler(500)
    def internal_server_error(error):
        return error_wrapper('errors/500.html', error, 500)

    @app.errorhandler(503)
    def service_unavailable(error):
        return error_wrapper('errors/503.html', error, 503)
