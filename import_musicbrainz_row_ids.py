from listenbrainz import config, db
from brainzutils import musicbrainz_db

import listenbrainz.db.user as db_user
import sqlalchemy

def import_musicbrainz_rows(musicbrainz_db_uri):
    musicbrainz_db.init_db_engine(musicbrainz_db_uri)
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    users = db_user.get_all_users()
    with musicbrainz_db.engine.connect() as mb_connection:
        with db.engine.connect() as connection:
            for user in users:
                if user['musicbrainz_row_id'] is not None:
                    continue
                name = user['musicbrainz_id']
                result = mb_connection.execute(sqlalchemy.text("""
                        SELECT id
                          FROM editor
                         WHERE LOWER(name) = LOWER(:name)
                    """), {
                        'name': name,
                    })
                musicbrainz_row_id = None
                if result.rowcount > 0:
                    musicbrainz_row_id = result.fetchone()['id']
                else:
                    print('No user with specified username in the MusicBrainz db: %s' % name)
                    continue

                connection.execute(sqlalchemy.text("""
                        UPDATE "user"
                           SET musicbrainz_row_id = :musicbrainz_row_id
                         WHERE id = :id
                    """), {
                        'musicbrainz_row_id': musicbrainz_row_id,
                        'id': user['id'],
                    })
                print('Inserted row_id %d for user %s' % (musicbrainz_row_id, name))


if __name__ == '__main__':
    import_musicbrainz_rows(config.MB_DATABASE_URI)
