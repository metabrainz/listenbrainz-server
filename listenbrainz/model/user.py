from datetime import datetime
from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


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
    user_login_id = db.Column(db.String)

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
        'user_login_id',
    ]
    column_searchable_list = [
        'id',
        'musicbrainz_row_id',
    ]

    column_filters = [
        'created',
        'gdpr_agreed',
        'last_login',
        'latest_import',
    ]
