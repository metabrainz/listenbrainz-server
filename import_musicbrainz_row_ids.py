from listenbrainz import config, db
from brainzutils import musicbrainz_db

import listenbrainz.db.user as db_user
import sqlalchemy


def fix_username_for_exceptions():
    with db.engine.connect() as connection:
        # 2106 - Fée Deuspi
        connection.execute(sqlalchemy.text("""
            UPDATE "user"
               SET musicbrainz_id = 'Fée Deuspi'
             WHERE id = 2106
            """))

        # 243 - ClæpsHydra
        connection.execute(sqlalchemy.text("""
            UPDATE "user"
               SET musicbrainz_id = 'ClæpsHydra'
             WHERE id = 243
            """))


def import_musicbrainz_rows(musicbrainz_db_uri, dry_run=True):
    musicbrainz_db.init_db_engine(musicbrainz_db_uri)
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    users = db_user.get_all_users()
    import_count = 0
    already_imported = 0
    not_found = 0
    deleted = 0
    fix_username_for_exceptions()
    with musicbrainz_db.engine.connect() as mb_connection:
        with db.engine.connect() as connection:
            for user in users:
                if user['musicbrainz_row_id'] is not None:
                    already_imported += 1
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
                    import_count += 1
                else:
                    print('No user with specified username in the MusicBrainz db: %s' % name)
                    not_found += 1
                    continue

                if not dry_run:
                    connection.execute(sqlalchemy.text("""
                            UPDATE "user"
                               SET musicbrainz_row_id = :musicbrainz_row_id
                             WHERE id = :id
                        """), {
                            'musicbrainz_row_id': musicbrainz_row_id,
                            'id': user['id'],
                        })
                    print('Inserted row_id %d for user %s' % (musicbrainz_row_id, name))
    print('Total number of ListenBrainz users: %d' % len(users))
    print('Total number of ListenBrainz users with already imported row ids: %d' % already_imported)
    print('Total number of ListenBrainz users whose row ids can be imported: %d' % import_count)
    print('Total number of ListenBrainz users not found in MusicBrainz: %d' % not_found)
    print('Total number of ListenBrainz users deleted from MusicBrainz: %d' % deleted)


if __name__ == '__main__':
    import_musicbrainz_rows(config.MB_DATABASE_URI, dry_run=config.MUSICBRAINZ_IMPORT_DRY_RUN)
