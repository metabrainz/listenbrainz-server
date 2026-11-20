from flask import g, jsonify

from listenbrainz.mbid_mapping_writer.typesense_utils import TYPESENSE_UNAVAILABLE_MESSAGE


def init_error_handlers(app):
    @app.after_request
    def typesense_unavailable(response):
        # Dataset Hoster handles query exceptions internally, so a Flask error
        # handler cannot set the status for an unavailable search backend.
        if g.pop("typesense_unavailable", False):
            response = jsonify(code=503, error=TYPESENSE_UNAVAILABLE_MESSAGE)
            response.status_code = 503
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Cache-Control"] = "no-store"
        return response
