from datetime import datetime, timezone

from flask import current_app,flash,redirect
from flask_admin.model import action
from psycopg2 import OperationalError, DatabaseError
from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link, set_users_paused
from listenbrainz.webserver.admin import AdminModelView
from listenbrainz.background.background_tasks import add_task
from listenbrainz.webserver import create_app, db_conn, ts_conn


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
    musicbrainz_id = db.Column(db.String)
    auth_token = db.Column(db.String)
    last_login = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False)
    latest_import = db.Column(db.DateTime(timezone=True), default=lambda: datetime.fromtimestamp(0, tz=timezone.utc))
    gdpr_agreed = db.Column(db.DateTime(timezone=True))
    musicbrainz_row_id = db.Column(db.Integer, nullable=False)
    login_id = db.Column(db.String)
    is_paused = db.Column(db.Boolean, nullable=False)


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
        'last_login',
        'latest_import',
        'login_id',
        'is_paused',
        'gdpr_agreed',
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
        'is_paused',
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


    # With select action to pause users.
    @action(
        name="pause_users",  # Unique name for the action
        text="Pause", 
        confirmation="Pause selected users?",
    )
    def pause_users(self, ids):
        try:
            users = set_users_paused(db_conn, ids, True)
            flash(f"Paused {len(users)} users", "success")
        except Exception as e:
            flash(f"Failed to pause users: {str(e)}", "error")
        return redirect('/admin/user_model/')


    # With select action to unpause users.
    @action(
        name="unpause_users",
        text="Unpause", 
        confirmation="Unpause selected users?",
    )
    def unpause_users(self, ids):
        try:
            users = set_users_paused(db_conn, ids, False)
            flash(f"Unpaused {len(users)} users", "success")
        except Exception as e:
            flash(f"Failed to unpause users: {str(e)}", "error")
        return redirect('/admin/user_model/')
