from functools import update_wrapper, wraps

from flask import request, current_app, make_response, redirect, url_for

from listenbrainz.webserver import timescale_connection


def crossdomain(f):
    """ Decorator to add CORS headers to flask endpoints """
    @wraps(f)
    def decorator(*args, **kwargs):
        options_resp = current_app.make_default_options_response()

        if request.method == 'OPTIONS':
            resp = options_resp
        else:
            resp = make_response(f(*args, **kwargs))

        h = resp.headers
        h["Access-Control-Allow-Origin"] = "*"
        h["Access-Control-Allow-Methods"] = options_resp.headers["allow"]
        h["Access-Control-Max-Age"] = "21600"
        h["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return resp

    f.provide_automatic_options = False
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
