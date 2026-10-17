""" Migrate user data export archives from the on-disk export directory to Garage.

User data exports used to be written to a directory shared between the webserver and the
background tasks container (the USER_DATA_EXPORT_BASE_DIR docker volume), they are stored in
the Garage bucket named by GARAGE_USER_DATA_EXPORT_BUCKET now. This uploads the archives that
are still on disk, using the filename recorded in user_data_export as the object name so that
the existing rows keep working unchanged.

Uploads are skipped for archives that already exist in the bucket, so the migration can be run
again after a partial run. Files without a matching user_data_export row are left alone (or
removed with --delete-source), they are the ones the cleanup cronjob would have deleted anyway.
Completed exports whose archive exists neither in the bucket nor on disk cannot be migrated, so
they are marked as failed and the user is asked to create a new export. Because that is a
destructive and irreversible update, it is skipped unless the directory actually contained
archives belonging to a completed export; pass --mark-missing-failed to do it anyway.
"""
from collections import defaultdict
from pathlib import Path

import click
from flask import current_app
from sqlalchemy import text

from listenbrainz.garage import bucket_exists, ensure_bucket, get_garage_client, \
    get_user_data_export_bucket, list_object_names

ARCHIVE_MISSING_PROGRESS = "Export archive is no longer available, please create a new export."


def get_completed_exports(db_conn) -> dict[str, list[int]]:
    """ Get the export ids of all completed exports, keyed by the archive's filename. """
    result = db_conn.execute(text("""
        SELECT id, filename
          FROM user_data_export
         WHERE status = 'completed'
           AND filename IS NOT NULL
    """))
    exports = defaultdict(list)
    for row in result:
        exports[row.filename].append(row.id)
    return exports


def get_all_export_filenames(db_conn) -> set[str]:
    """ Get the archive filenames of all exports, whatever their status.

    Only completed exports are migrated but an archive belonging to an export in any other
    status is not an orphan either, so it must not be deleted by --delete-source.
    """
    result = db_conn.execute(text("SELECT filename FROM user_data_export WHERE filename IS NOT NULL"))
    return {row.filename for row in result}


def mark_exports_failed(db_conn, export_ids: list[int]):
    """ Mark the given exports as failed so that the user is asked to create a new one. """
    db_conn.execute(text("""
        UPDATE user_data_export
           SET status = 'failed'
             , progress = :progress
         WHERE id = ANY(:export_ids)
    """), {"export_ids": export_ids, "progress": ARCHIVE_MISSING_PROGRESS})
    db_conn.commit()


def migrate_exports(db_conn, export_dir: str, delete_source: bool = False, dry_run: bool = False,
                    mark_missing_failed: bool = False):
    """ Upload the user data export archives in export_dir to garage and update the database. """
    source_dir = Path(export_dir)
    if not source_dir.is_dir():
        raise click.ClickException(f"Export directory does not exist: {export_dir}")

    client = get_garage_client()
    bucket = get_user_data_export_bucket()
    if dry_run:
        # the bucket is created by ops in production but may not exist yet, a dry run should
        # still report what it would do instead of erroring out with NoSuchBucket
        bucket_available = bucket_exists(client, bucket)
        if not bucket_available:
            current_app.logger.info("Bucket %s does not exist yet, it would be created", bucket)
    else:
        ensure_bucket(client, bucket)
        bucket_available = True

    exports = get_completed_exports(db_conn)
    known_filenames = get_all_export_filenames(db_conn)
    # archives that do not need to be uploaded (again), this run's uploads are added as they happen
    available = set(list_object_names(client, bucket)) if bucket_available else set()
    files = sorted(path for path in source_dir.iterdir() if path.is_file())

    uploaded_count, skipped_count, orphan_count, pending_count = 0, 0, 0, 0

    for path in files:
        if path.name in exports:
            if path.name in available:
                current_app.logger.info("%s already exists in garage, not uploading it again", path.name)
                skipped_count += 1
            else:
                current_app.logger.info("Uploading %s (%d bytes)", path.name, path.stat().st_size)
                if not dry_run:
                    client.upload_file(str(path), bucket, path.name,
                                       ExtraArgs={"ContentType": "application/zip"})
                available.add(path.name)
                uploaded_count += 1
            deletable = True
        elif path.name in known_filenames:
            # the export is in progress or failed, only completed exports are migrated and the
            # archive must survive in case the export completes while the migration runs
            current_app.logger.info("%s does not belong to a completed export, leaving it alone", path.name)
            pending_count += 1
            deletable = False
        else:
            current_app.logger.info("No export exists for %s, not migrating it", path.name)
            orphan_count += 1
            deletable = True

        if delete_source and deletable and not dry_run:
            path.unlink(missing_ok=True)

    missing = {filename: ids for filename, ids in exports.items() if filename not in available}
    marked_failed = 0
    if missing:
        # every completed export looks missing if the wrong directory was passed or the export
        # volume was not mounted, refuse to fail all of them on the strength of an empty scan
        if uploaded_count + skipped_count == 0 and not mark_missing_failed:
            current_app.logger.warning(
                "%d completed export(s) have no archive but no archive of a completed export was found in %s"
                " either. Not marking them as failed, check the directory and re-run with"
                " --mark-missing-failed if this is expected.",
                len(missing), export_dir
            )
        else:
            current_app.logger.info(
                "Marking %d export(s) as failed, their archive is missing: %s",
                len(missing), ", ".join(sorted(missing))
            )
            marked_failed = len(missing)
            if not dry_run:
                mark_exports_failed(db_conn, [export_id for ids in missing.values() for export_id in ids])

    current_app.logger.info(
        "Migrated %d archive(s), %d already in garage, %d not completed yet, %d without an export,"
        " %d export(s) marked failed.",
        uploaded_count, skipped_count, pending_count, orphan_count, marked_failed
    )
