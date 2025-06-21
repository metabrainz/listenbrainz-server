from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


class FunkwhaleServer(db.Model):
    __tablename__ = 'funkwhale_servers'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    host_url = db.Column(db.String, nullable=False)
    client_id = db.Column(db.String)
    client_secret = db.Column(db.String)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    token_expiry = db.Column(db.DateTime(timezone=True))

    __table_args__ = (
        db.PrimaryKeyConstraint('user_id', 'host_url'),
    )

    user = db.relationship('User')


class FunkwhaleServerAdmin(AdminModelView):
    column_list = ('user_id', 'host_url', 'token_expiry')
    column_searchable_list = ('user_id', 'host_url')
    column_filters = ('user_id', 'host_url', 'token_expiry')
    form_columns = ('user_id', 'host_url', 'client_id', 'client_secret', 'access_token', 'refresh_token', 'token_expiry') 