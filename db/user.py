from db import create_cursor, commit
import uuid


def create(musicbrainz_id):
    with create_cursor() as cursor:
        # TODO(roman): Do we need to make sure that musicbrainz_id is case insensitive?
        cursor.execute("""INSERT INTO "user" (musicbrainz_id, auth_token)
                               VALUES (%s, %s)
                            RETURNING id""",
                       (musicbrainz_id, str(uuid.uuid4())))
        commit()
        new_id = cursor.fetchone()[0]
        return new_id


def get(id):
    """Get user with a specified ID (integer)."""
    with create_cursor() as cursor:
        query = """SELECT id
                        , created
                        , musicbrainz_id
                        , auth_token
                     FROM "user"
                    WHERE id = %s"""
        cursor.execute(query, (id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID."""
    with create_cursor() as cursor:
        cursor.execute(
            'SELECT id, created, musicbrainz_id, auth_token '
            'FROM "user" '
            'WHERE LOWER(musicbrainz_id) = LOWER(%s)',
            (musicbrainz_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_or_create(musicbrainz_id):
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
