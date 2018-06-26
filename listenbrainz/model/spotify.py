from datetime import datetime
from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


class Spotify(db.Model):
    __tablename__ = 'spotify_auth'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    user_token = db.Column(db.String, nullable=False)
    token_expires = db.Column(db.DateTime(timezone=True))
    refresh_token = db.Column(db.String, nullable=False)
    last_updated = db.Column(db.DateTime(timezone=True))
    latest_listened_at = db.Column(db.DateTime(timezone=True))
    active = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.String)


class SpotifyAdminView(AdminModelView):
    form_columns = [
        'user_id',
        'user_token',
        'token_expires',
        'refresh_token',
        'last_updated',
        'latest_listened_at',
        'active',
        'error_message',
    ]
    column_list = [
        'user_id',
        'token_expires',
        'latest_listened_at',
        'last_updated',
        'active',
        'error_message',
        'user_token',
        'refresh_token',
    ]

    column_searchable_list = [
        'user_id',
        'active'
    ]

    column_filters = [
        'active',
        'latest_listened_at',
        'last_updated',
        'token_expires',
    ]
