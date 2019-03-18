from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# import all models here please
from listenbrainz.model.spotify import Spotify
from listenbrainz.model.user import User
