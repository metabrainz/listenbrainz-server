from functools import wraps

from flask import request, current_app, make_response, redirect, url_for

from listenbrainz.webserver import timescale_connection


def cache_public(s_maxage):
    """Mark a public API GET as cacheable by shared caches for ``s_maxage`` seconds.

    Sets ``Cache-Control: public, max-age=0, s-maxage=<s_maxage>`` on 200s.
    ``add_cache_header`` leaves that in place and only defaults other
    responses to private. Place below ``@crossdomain`` and ``@ratelimit``
    so OPTIONS/429s never reach this wrapper.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            if resp.status_code == 200:
                resp.cache_control.private = False
                resp.cache_control.no_store = False
                resp.cache_control.public = True
                resp.cache_control.max_age = 0
                resp.cache_control.s_maxage = s_maxage
            return resp
        return wrapper
    return decorator


def crossdomain(f):
    """ Decorator to add CORS headers to flask endpoints.

    This decorator should be applied just after the route to ensure the provide_automatic_options
    is set correctly.
    """
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

    decorator.provide_automatic_options = False
    decorator.required_methods = ["OPTIONS"]
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
            return redirect(url_for("index.index_pages", page="listens-offline"))
        return func(*args, **kwargs)

    return decorator


def web_musicbrainz_needed(func):
    """
        This web decorator checks to see if musicbrainz db is online by checking
        a config variable and if not, it redirects to an error page telling the
        user that the musicbrainz db is offline.
    """
    @wraps(func)
    def decorator(*args, **kwargs):
        # if config item is missing, consider the database to be up (useful for local development)
        is_musicbrainz_up = current_app.config.get("IS_MUSICBRAINZ_UP", True)
        if not is_musicbrainz_up:
            return redirect(url_for("index.index_pages", page="musicbrainz-offline"))
        return func(*args, **kwargs)
    return decorator
