from functools import update_wrapper, wraps
from datetime import timedelta
from flask import request, current_app, make_response, redirect, url_for
from six import string_types

from listenbrainz.webserver import timescale_connection


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


def api_listenstore_needed(func):
    """
        This API decorator checks to see if timescale is online (by having
        a DB URI) and if not, it raises APIServiceUnavailable.
    """
    @wraps(func)
    def decorator(*args, **kwargs):
        from listenbrainz.webserver.errors import APIServiceUnavailable
        if timescale_connection._ts is None:
            raise APIServiceUnavailable("The listen database is momentarily offline. " +
                                        "Please wait a few minutes and try again.")
        return func(*args, **kwargs)

    return decorator


def web_listenstore_needed(func):
    """
        This web decorator checks to see if timescale is online (by having
        a DB URI) and if not, it redirects to an error page telling the user
        that the listenstore is offline.
    """
    @wraps(func)
    def decorator(*args, **kwargs):
        if timescale_connection._ts is None:
            return redirect(url_for("index.listens_offline"))
        return func(*args, **kwargs)

    return decorator
