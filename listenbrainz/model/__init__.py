from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# import all models here please
from listenbrainz.model.external_service_oauth import ExternalService
from listenbrainz.model.user import User
from listenbrainz.model.listens_import import ListensImporter
from listenbrainz.model.reported_users import ReportedUsers
from listenbrainz.model.playlist import Playlist
from listenbrainz.model.playlist_recording import PlaylistRecording
