from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView


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
        'reported_at'
    ]

    column_formatters = {
        "reporter.musicbrainz_id": lambda view, context, model, name: generate_username_link(model.reporter.musicbrainz_id),
        "reported.musicbrainz_id": lambda view, context, model, name: generate_username_link(model.reported.musicbrainz_id)
    }
