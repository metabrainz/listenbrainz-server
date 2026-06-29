from listenbrainz.model import db
from listenbrainz.db import user as db_user
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.admin import AdminModelView
from flask_admin.model import action
from flask import  flash, redirect


class ReportedUsers(db.Model):
    __tablename__ = 'reported_users'

    id = db.Column(db.Integer, primary_key=True)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    reported_at = db.Column(db.DateTime(timezone=True))
    reason = db.Column(db.String)
    reporter = db.relationship('User', foreign_keys=[reporter_user_id])
    reported = db.relationship('User', foreign_keys=[reported_user_id])


class ReportedUserAdminView(AdminModelView):
    column_list = [
        'id',
        'reporter.musicbrainz_id',
        'reported.musicbrainz_id',
        'reason',
        'reported_at',
        'reported.is_paused',
    ]

    column_formatters = {
        "reporter.musicbrainz_id": lambda view, context, model, name: generate_username_link(model.reporter.musicbrainz_id),
        "reported.musicbrainz_id": lambda view, context, model, name: generate_username_link(model.reported.musicbrainz_id)
    }

    # With select action to pause users.
    @action(
        name="pause_users",  # Unique name for the action
        text="Pause",
        confirmation="Pause selected users?",
    )
    def pause_users(self, ids):
        for user_id in ids:
            # making sure user_id is valid
            user = ReportedUsers.query.get(user_id)
            if user:
                try:
                    db_user.pause(db_conn, user.id)
                    db_conn.commit()
                    flash(f"{user.musicbrainz_id} paused", "success")
                except Exception as e:
                    flash(
                        f"Failed for {user.musicbrainz_id}: {str(e)}", "error")
            else:
                flash(f"{user_id} not found!", "error")
        return redirect('/admin/reported_users_model/')

    # With select action to unpause users.
    @action(
        name="unpause_users",
        text="Unpause",
        confirmation="Unpause selected users?",
    )
    def unpause_users(self, ids):
        for user_id in ids:
            # making sure user_id is valid
            user = ReportedUsers.query.get(user_id)
            if user:
                try:
                    db_user.unpause(db_conn, user.id)
                    db_conn.commit()
                    flash(f"{user.musicbrainz_id} unpaused", "success")
                except Exception as e:
                    flash(
                        f"Failed for {user.musicbrainz_id}: {str(e)}", "error")
            else:
                flash(f"{user_id} not found!", "error")
        return redirect('/admin/reported_users_model/')
