from datetime import datetime

from flask import current_app
from psycopg2 import OperationalError, DatabaseError
from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView
from listenbrainz.background.background_tasks import add_task


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    musicbrainz_id = db.Column(db.String)
    auth_token = db.Column(db.String)
    last_login = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    latest_import = db.Column(db.DateTime(timezone=True), default=lambda: datetime.fromutctimestamp(0))
    gdpr_agreed = db.Column(db.DateTime(timezone=True))
    musicbrainz_row_id = db.Column(db.Integer, nullable=False)
    login_id = db.Column(db.String)


class UserAdminView(AdminModelView):
    form_columns = [
        'musicbrainz_id',
        'musicbrainz_row_id',
    ]
    column_list = [
        'id',
        'musicbrainz_id',
        'musicbrainz_row_id',
        'created',
        'auth_token',
        'gdpr_agreed',
        'last_login',
        'latest_import',
        'login_id',
    ]
    column_searchable_list = [
        'id',
        'musicbrainz_row_id',
        'musicbrainz_id'
    ]

    column_filters = [
        'created',
        'gdpr_agreed',
        'last_login',
        'latest_import',
        'id',
        'musicbrainz_id',
        'musicbrainz_row_id',
    ]

    column_formatters = {
        "musicbrainz_id": lambda view, context, model, name: generate_username_link(model.musicbrainz_id)
    }

    def delete_model(self, model):
        try:
            add_task(model.id, "delete_user")
            return True
        except OperationalError or DatabaseError as err:
            current_app.logger.error(err, exc_info=True)
            return False
