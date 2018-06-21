from listenbrainz import db
from brainzutils import musicbrainz_db
from listenbrainz.webserver import create_app
from listenbrainz.webserver.views.api_tools import publish_data_to_queue
from listenbrainz.listenstore import InfluxListenStore
from listenbrainz.webserver.influx_connection import init_influx_connection
from werkzeug.exceptions import NotFound

import listenbrainz.db.user as db_user
import logging
import sqlalchemy

app = create_app()
influx = init_influx_connection(logging, {
            'REDIS_HOST': app.config['REDIS_HOST'],
            'REDIS_PORT': app.config['REDIS_PORT'],
            'REDIS_NAMESPACE': app.config['REDIS_NAMESPACE'],
            'INFLUX_HOST': app.config['INFLUX_HOST'],
            'INFLUX_PORT': app.config['INFLUX_PORT'],
            'INFLUX_DB_NAME': app.config['INFLUX_DB_NAME'],
        })


def update_row_ids_for_exceptions():
    with brainzutils.musicbrainz_db.connect() as mb_connection:
        with db.engine.connect() as connection:
            # 2106 - Fée Deuspi
            result = mb_connection.execute(sqlalchemy.text("""
                SELECT id
                  FROM editor
                 WHERE name = 'Fée Deuspi'
                """))

            mb_row_id = result.fetchone()['id']
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET musicbrainz_row_id = :mb_row_id
                 WHERE id = 2106
                """), {
                    'mb_row_id': mb_row_id,
                })

            # 243 - ClæpsHydra
            result = mb_connection.execute(sqlalchemy.text("""
                SELECT id
                  FROM editor
                 WHERE name = 'ClæpsHydra'
                """))

            mb_row_id = result.fetchone()['id']
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET musicbrainz_row_id = :mb_row_id
                 WHERE id = 243
                """), {
                    'mb_row_id': mb_row_id,
                })


def delete_user(user):
    influx.delete(user['musicbrainz_id'])
    publish_data_to_queue(
        data={
            'type': 'delete.user',
            'musicbrainz_id': user['musicbrainz_id'],
        },
        exchange=app.config['BIGQUERY_EXCHANGE'],
        queue=app.config['BIGQUERY_QUEUE'],
        error_msg='Could not upt user %s into queue for bq deletion.' % user['musicbrainz_id'],
    )
    db_user.delete(user['id'])


def import_musicbrainz_rows(musicbrainz_db_uri, dry_run=True):
    musicbrainz_db.init_db_engine(musicbrainz_db_uri)
    db.init_db_connection(app.config['SQLALCHEMY_DATABASE_URI'])
    users = db_user.get_all_users()
    import_count = 0
    already_imported = 0
    not_found = 0
    deleted = 0

    if not dry_run:
        update_row_ids_for_exceptions()
    with musicbrainz_db.engine.connect() as mb_connection:
        with db.engine.connect() as connection:
            for user in users:
                if user.get('musicbrainz_row_id') is not None:
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
                    if not dry_run:
                        print('Deleting user %s' % name)
                        try:
                            delete_user(user)
                        except NotFound:
                            print('User %s not found in LB...' % name)
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
    import_musicbrainz_rows(
        app.config['MB_DATABASE_URI'],
        dry_run=app.config['MUSICBRAINZ_IMPORT_DRY_RUN'],
    )
