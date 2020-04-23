from functools import update_wrapper, wraps
from datetime import timedelta
from flask import request, current_app, make_response
from six import string_types
from werkzeug.exceptions import Forbidden


def crossdomain(origin='*', methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    # Based on snippet by Armin Ronacher located at http://flask.pocoo.org/snippets/56/.
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, string_types):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, string_types):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


def ip_filter(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.config.get('IP_FILTER_ON', False):
            if current_app.config.get('BEHIND_GATEWAY', False):
                ip_addr = request.headers.get(current_app.config['REMOTE_ADDR_HEADER'])
            else:
                ip_addr = request.remote_addr
            if ip_addr not in current_app.config['IP_WHITELIST']:
                raise Forbidden
        return f(*args, **kwargs)

    return decorated
