from flask import render_template, make_response


def init_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(error):
        resp = make_response(render_template('errors/400.html', error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # TODO: 401 handler

    @app.errorhandler(403)
    def forbidden(error):
        resp = make_response(render_template('errors/403.html', error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    @app.errorhandler(404)
    def not_found(error):
        resp = make_response(render_template('errors/404.html', error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 404

    @app.errorhandler(500)
    def internal_server_error(error):
        resp = make_response(render_template('errors/500.html', error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    @app.errorhandler(503)
    def service_unavailable(error):
        resp = make_response(render_template('errors/503.html', error=error))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 503
