from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


class ReportedUsers(db.Model):
    __tablename__ = 'reported_users'

    id = db.Column(db.Integer, primary_key=True)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    reported_at = db.Column(db.DateTime(timezone=True))

    reporter = db.relationship('User', foreign_keys=[reporter_user_id])
    reported = db.relationship('User', foreign_keys=[reported_user_id])


class ReportedUserAdminView(AdminModelView):
    column_list = [
        'id',
        'reporter',
        'reported',
        'reported_at'
    ]

    column_formatters = dict(
        reporter=lambda view, context, model, name: model.reporter.musicbrainz_id,
        reported=lambda view, context, model, name: model.reported.musicbrainz_id
    )
