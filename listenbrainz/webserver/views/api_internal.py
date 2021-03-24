from brainzutils import metrics
from flask import Blueprint, jsonify

# These views expose internal statistics for use in the MetaBrainz logging sytem
# you're welcome to look at them youselves, but they are not supported outside
# of our infrastructure

api_internal = Blueprint('api_internal', __name__)


@api_internal.route('/statistics')
def statistics():
    return jsonify(metrics.stats())


@api_internal.route('/counter/<metric_name>')
def statistics_counter(metric_name):
    return jsonify(metrics.stats_count(metric_name))
