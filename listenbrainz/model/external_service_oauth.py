from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView


class ExternalService(db.Model):
    __tablename__ = 'external_service_oauth'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    # Workaround: cannot use Enum here because it seems SQLAlchemy uses the variable names of the enum instead of
    # the values assigned to them. It is possible to write a wrapper to change this behaviour but for our purposes
    # just using a string works fine so not going into that.
    service = db.Column(db.String, nullable=False)
    access_token = db.Column(db.String, nullable=False)
    refresh_token = db.Column(db.String)
    token_expires = db.Column(db.DateTime(timezone=True))
    last_updated = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    scopes = db.Column(db.ARRAY(db.String))
    user = db.relationship('User')


class ExternalServiceAdminView(AdminModelView):
    form_columns = [
        'id',
        'user_id',
        'service',
        'access_token',
        'refresh_token',
        'token_expires',
        'last_updated',
        'scopes'
    ]

    column_list = [
        'id',
        'user_id',
        'user_name',
        'service',
        'access_token',
        'refresh_token',
        'token_expires',
        'last_updated',
        'scopes'
    ]

    column_searchable_list = [
        'user_id',
        'service',
    ]

    column_filters = [
        'user_id',
        'service',
        'last_updated',
        'token_expires',
    ]

    column_formatters = {
        "user_name": lambda view, context, model, name: generate_username_link(model.user.musicbrainz_id)
    }
