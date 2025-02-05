from datetime import datetime

from flask import current_app,flash,redirect
from flask_admin.model import action
from psycopg2 import OperationalError, DatabaseError
from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView
from listenbrainz.background.background_tasks import add_task
from listenbrainz.db import user as db_user
from listenbrainz.webserver import create_app, db_conn, ts_conn


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
        for user_id in ids:
            # making sure user_id is valid
            user = User.query.get(user_id)
            if user:
                try:
                    db_user.pause(db_conn,user.id)
                    db_conn.commit()
                    flash(f"{user.musicbrainz_id} paused", "success")
                except Exception as e:
                    flash(f"Failed for {user.musicbrainz_id}: {str(e)}", "error")
            else:
                flash(f"{user_id} not found!", "error")
        return redirect('/admin/user_model/')


    # With select action to unpause users.
    @action(
        name="unpause_users",
        text="Unpause", 
        confirmation="Unpause selected users?",
    )
    def unpause_users(self, ids):
        for user_id in ids:
            # making sure user_id is valid
            user = User.query.get(user_id)
            if user:
                try:
                    db_user.unpause(db_conn,user.id)
                    db_conn.commit()
                    flash(f"{user.musicbrainz_id} unpaused", "success")
                except Exception as e:
                    flash(f"Failed for {user.musicbrainz_id}: {str(e)}", "error")
            else:
                flash(f"{user_id} not found!", "error")
        return redirect('/admin/user_model/')
