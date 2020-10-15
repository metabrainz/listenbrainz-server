# Internal metrics stored by LB for use in MetaBrainz monitoring systems
from flask import Blueprint, jsonify

from brainzutils import metrics

api_metrics_bp = Blueprint('api_metrics', __name__)


@api_metrics_bp.route('/increment/<metric_name>')
def increment_metric(metric_name):
    metrics.increment(metric_name)
    return jsonify({'status': 'ok'})


@api_metrics_bp.route('/stats/<metric_name>')
def stats(metric_name):
    return jsonify(metrics.stats(metric_name))