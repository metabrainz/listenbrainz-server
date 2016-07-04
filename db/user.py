import db
import uuid
import sqlalchemy

def create(musicbrainz_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""INSERT INTO "user" (musicbrainz_id, auth_token)
                                            VALUES (:mb_id, :token)
                                         RETURNING id""" ),
                                    {"mb_id": musicbrainz_id, "token": str(uuid.uuid4())})
        return result.fetchone()["id"]


def get(id):
    """Get user with a specified ID (integer)."""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT id, created, musicbrainz_id, auth_token
                                         FROM "user"
                                        WHERE id = :id"""),
                                    {"id": id})
        row = result.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID."""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT id, created, musicbrainz_id, auth_token
                                         FROM "user"
                                        WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)"""),
                                    {"mb_id": musicbrainz_id})
        row = result.fetchone()
        return dict(row) if row else None


def get_by_token(token):
    """Get user from an auth token"""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT id, created, musicbrainz_id
                                         FROM "user"
                                        WHERE auth_token = :auth_token"""),
                                    {"auth_token": token})
        row = result.fetchone()
        return dict(row) if row else None


def get_or_create(musicbrainz_id):
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
