from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView

from sqlalchemy.dialects.postgresql import JSONB



class ListensImporter(db.Model):
    __tablename__ = 'listens_importer'

    id = db.Column(db.Integer, primary_key=True)
    external_service_oauth_id = db.Column(db.Integer, db.ForeignKey('external_service_oauth.id', ondelete='SET NULL'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    # Workaround: cannot use Enum here because it seems SQLAlchemy uses the variable names of the enum instead of
    # the values assigned to them. It is possible to write a wrapper to change this behaviour but for our purposes
    # just using a string works fine so not going into that.
    service = db.Column(db.String, nullable=False)
    last_updated = db.Column(db.DateTime(timezone=True))
    latest_listened_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(JSONB)
    error = db.Column(JSONB)
    user = db.relationship('User')


class ListensImporterAdminView(AdminModelView):
    form_columns = [
        'id',
        'user_id',
        'external_service_oauth_id',
        'service',
        'last_updated',
        'latest_listened_at',
        'status',
        'error'
    ]

    column_list = [
        'id',
        'user_id',
        'user_name',
        'external_service_oauth_id',
        'service',
        'last_updated',
        'latest_listened_at',
        'status',
        'error'
    ]

    column_searchable_list = [
        'user_id',
        'service',
        'error'
    ]

    column_filters = [
        'user_id',
        'service',
        'last_updated',
        'error',
        'latest_listened_at'
    ]

    column_formatters = {
        "user_name": lambda view, context, model, name: generate_username_link(model.user.musicbrainz_id)
    }
