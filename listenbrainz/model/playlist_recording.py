import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from listenbrainz.model import db
from listenbrainz.webserver.admin import AdminModelView


class PlaylistRecording(db.Model):
    __bind_key__ = "timescale"
    __tablename__ = "playlist_recording"
    __table_args__ = {"schema": "playlist"}

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlist.playlist.id", ondelete="CASCADE"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    mbid = db.Column(UUID(as_uuid=True), nullable=False)
    added_by_id = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime(timezone=True), nullable=False)

    def __str__(self):
        return str(self.mbid)


class PlaylistRecordingAdminView(AdminModelView):
    column_list = ['playlist', 'position', 'mbid', 'added_by_id', 'created']
