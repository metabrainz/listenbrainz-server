from flask import current_app
from sqlalchemy import text

from listenbrainz.background.listens_importer.librefm import LibrefmListensImporter
from listenbrainz.background.listens_importer.listenbrainz import ListenBrainzListensImporter
from listenbrainz.background.listens_importer.maloja import MalojaListensImporter
from listenbrainz.background.listens_importer.spotify import SpotifyListensImporter


def import_listens(db_conn, ts_conn, user_id, bg_task_metadata):
    """Main entry point for importing listens."""
    import_id = bg_task_metadata["import_id"]

    result = db_conn.execute(text("""
      SELECT *
        FROM user_data_import
       WHERE id = :import_id
    """), {"import_id": import_id})

    import_task = result.mappings().first()
    if import_task is None:
        current_app.logger.error("No import with import_id: %s, skipping.", import_id)
        return

    import_task = dict(import_task)
    service = import_task["service"]
    if service == "spotify":
        importer = SpotifyListensImporter(db_conn, ts_conn)
    elif service == "listenbrainz":
        importer = ListenBrainzListensImporter(db_conn, ts_conn)
    elif service == "librefm":
        importer = LibrefmListensImporter(db_conn, ts_conn)
    elif service == "maloja":
        importer = MalojaListensImporter(db_conn, ts_conn)
    else:
        raise ValueError(f"Unsupported service: {service}")
    importer.import_listens(user_id, import_task)
