from __future__ import print_function
from flask import Blueprint
from werkzeug.exceptions import NotFound


# Blueprint to contain the view that returns 404 if API calls are made to
# the web app instead of the api flask application
api_404_bp = Blueprint('api_404', __name__)


@api_404_bp.route('/1/submit_listens', methods=['GET', 'POST'])
@api_404_bp.route('/1/user/<user_name>/listens', methods=['GET'])
@api_404_bp.route('/2.0/', methods=['GET', 'POST'])
@api_404_bp.route('/api/auth/', methods=['GET', 'POST'])
def webapp_api_call(user_name=None):
    """
    Insert documentation here
    """
    raise NotFound("Invalid call to API, please use api.listenbrainz.org instead")
