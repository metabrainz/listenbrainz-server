import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID, JSONB

from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


class Playlist(db.Model):
    __bind_key__ = "timescale"
    __tablename__ = "playlist"
    __table_args__ = {"schema": "playlist"}

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    mbid = db.Column(UUID(as_uuid=True), nullable=False)
    creator_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    public = db.Column(db.Boolean, nullable=False)
    created = db.Column(db.DateTime(timezone=True), nullable=False)
    last_updated = db.Column(db.DateTime(timezone=True), nullable=False)
    copied_from_id = db.Column(db.Integer)
    created_for_id = db.Column(db.Integer)
    additional_metadata = db.Column(JSONB)

    recordings = db.relationship("PlaylistRecording", backref="playlist")

    def __str__(self):
        return self.name


class PlaylistAdminView(AdminModelView):
    # Flask-Admin blows up if a jsonb column is added to the filter
    columns_without_jsonb = [
        "id",
        "mbid",
        "creator_id",
        "name",
        "description",
        "public",
        "created",
        "last_updated",
        "copied_from_id",
        "created_for_id",
    ]
    column_searchable_list = columns_without_jsonb
    column_filters = columns_without_jsonb
    column_list = columns_without_jsonb + ["recordings", "additional_metadata"]
