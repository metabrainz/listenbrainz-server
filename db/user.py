from db import db
import uuid


def create(musicbrainz_id):
    # TODO(roman): Do we need to make sure that musicbrainz_id is case insensitive?
    result = db.session.execute("""INSERT INTO "user" (musicbrainz_id, auth_token)
                                        VALUES (:mb_id, :token)
                                     RETURNING id""",
                                {"mb_id": musicbrainz_id, "token": str(uuid.uuid4())})
    db.session.commit()
    return result.fetchone()["id"]


def get(id):
    """Get user with a specified ID (integer)."""
    result = db.session.execute("""SELECT id, created, musicbrainz_id, auth_token
                                     FROM "user"
                                    WHERE id = :id""",
                                {"id": id})
    row = result.fetchone()
    return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID."""
    result = db.session.execute("""SELECT id, created, musicbrainz_id, auth_token
                                     FROM "user"
                                    WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)""",
                                {"mb_id": musicbrainz_id})
    row = result.fetchone()
    return dict(row) if row else None


def get_or_create(musicbrainz_id):
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
